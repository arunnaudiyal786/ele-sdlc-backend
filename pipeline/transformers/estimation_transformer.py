"""
Estimation entity transformer.

Transforms extracted document data to Estimation schema.
Typically processes rows from estimation Excel spreadsheets.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Type

from pipeline.core.id_generator import IDGenerator
from pipeline.core.relationship_manager import RelationshipManager
from pipeline.extractors.base import ExtractedData
from pipeline.transformers.base import BaseTransformer, TransformationError, TransformationResult
from pipeline.transformers.normalizers import (
    clean_text,
    date_normalizer,
    dict_to_json_string,
    email_normalizer,
    enum_normalizer,
    number_normalizer,
    integer_normalizer,
)
from shared.schemas.estimation import Estimation


class EstimationTransformer(BaseTransformer[Estimation]):
    """
    Transforms extracted data to Estimation entities.

    Handles:
    - Table row processing (from Excel)
    - ID and module ID generation
    - Effort hours calculation
    - Relationship linking to epics
    """

    def get_target_schema(self) -> Type[Estimation]:
        return Estimation

    async def transform(
        self,
        extracted: ExtractedData,
        mapping: Dict[str, str],
        id_gen: IDGenerator,
        rel_mgr: RelationshipManager,
        position: int = 0,
    ) -> TransformationResult[Estimation]:
        """
        Transform a single extraction to Estimation entity.

        For table-based extractions, use transform_row() instead.
        """
        # If extraction has tables, transform first row
        rows = self._get_table_rows(extracted)
        if rows:
            return await self.transform_row(
                rows[0], mapping, id_gen, rel_mgr, position
            )

        # No table data - use fields directly
        return await self._transform_from_fields(
            extracted, mapping, id_gen, rel_mgr, position
        )

    async def transform_row(
        self,
        row: Dict[str, Any],
        mapping: Dict[str, str],
        id_gen: IDGenerator,
        rel_mgr: RelationshipManager,
        position: int = 0,
        epic_id: Optional[str] = None,
    ) -> TransformationResult[Estimation]:
        """
        Transform a single table row to Estimation entity.

        Args:
            row: Row dictionary from extraction
            mapping: Field mapping
            id_gen: ID generator
            rel_mgr: Relationship manager
            position: Position index
            epic_id: Optional explicit epic ID to link to

        Returns:
            TransformationResult with Estimation
        """
        errors = []
        warnings = []

        try:
            # Generate IDs
            dev_est_id = id_gen.generate_estimation_id()

            # Resolve epic_id if not provided
            if not epic_id:
                epic_id = rel_mgr.get_epic_by_position(position)
            if not epic_id:
                # Create a placeholder epic ID if none exists
                warnings.append(
                    TransformationError(
                        field_name="epic_id",
                        message="No epic found for position, using first epic or generating",
                        severity="warning",
                    )
                )
                epic_id = rel_mgr.get_epic_by_position(0)
                if not epic_id:
                    epic_id = id_gen.generate_epic_id()
                    rel_mgr.register_epic(epic_id, f"auto_epic_{position}")

            # Get task description - try multiple column names
            task_desc = self._get_row_value(
                row, mapping, "task_description",
                fallback_keys=["description", "task", "module", "feature", "Description", "Task"]
            )
            task_desc = clean_text(task_desc) or f"Task {position + 1}"

            # Generate module ID from domain hint
            domain = self._infer_domain(task_desc, row)
            module_id = id_gen.generate_module_id(domain)

            # Complexity
            complexity = self._get_row_value(
                row, mapping, "complexity",
                fallback_keys=["size", "Complexity", "Size", "t_shirt_size"]
            )
            complexity = enum_normalizer(
                complexity,
                ["Small", "Medium", "Large"],
                default="Medium"
            )

            # Effort hours
            dev_hours = self._get_row_value(
                row, mapping, "dev_effort_hours",
                fallback_keys=["dev_hours", "development", "Dev Hours", "Dev Effort"]
            )
            dev_hours = number_normalizer(dev_hours, 0.0)

            qa_hours = self._get_row_value(
                row, mapping, "qa_effort_hours",
                fallback_keys=["qa_hours", "testing", "QA Hours", "QA Effort", "Test Hours"]
            )
            qa_hours = number_normalizer(qa_hours, 0.0)

            total_hours = self._get_row_value(
                row, mapping, "total_effort_hours",
                fallback_keys=["total_hours", "Total Hours", "Total"]
            )
            total_hours = number_normalizer(total_hours, 0.0)
            if total_hours == 0:
                total_hours = dev_hours + qa_hours

            # Story points
            story_points = self._get_row_value(
                row, mapping, "total_story_points",
                fallback_keys=["story_points", "points", "Story Points", "SP"]
            )
            story_points = integer_normalizer(story_points, 0)

            # Risk level
            risk = self._get_row_value(
                row, mapping, "risk_level",
                fallback_keys=["risk", "Risk", "Risk Level"]
            )
            risk = enum_normalizer(risk, ["Low", "Medium", "High"], default="Medium")

            # Estimation method
            method = self._get_row_value(
                row, mapping, "estimation_method",
                fallback_keys=["method", "Method", "Estimation Method"]
            )
            method = clean_text(method) or "Planning Poker"

            # Confidence level
            confidence = self._get_row_value(
                row, mapping, "confidence_level",
                fallback_keys=["confidence", "Confidence"]
            )
            confidence = enum_normalizer(
                confidence, ["Low", "Medium", "High"], default="Medium"
            )

            # Estimated by
            estimated_by = self._get_row_value(
                row, mapping, "estimated_by",
                fallback_keys=["estimator", "by", "Estimated By", "Owner"]
            )
            estimated_by = email_normalizer(estimated_by) or "unknown@company.com"

            # Estimation date
            est_date = self._get_row_value(
                row, mapping, "estimation_date",
                fallback_keys=["date", "Date", "Estimation Date"]
            )
            est_date = date_normalizer(est_date)

            # Other params - collect any unmapped columns
            other_params = self._collect_other_params(row, mapping)

            # Create Estimation entity
            estimation = Estimation(
                dev_est_id=dev_est_id,
                epic_id=epic_id,
                module_id=module_id,
                task_description=task_desc,
                complexity=complexity,
                dev_effort_hours=dev_hours,
                qa_effort_hours=qa_hours,
                total_effort_hours=total_hours,
                total_story_points=story_points,
                risk_level=risk,
                estimation_method=method,
                confidence_level=confidence,
                estimated_by=estimated_by,
                estimation_date=est_date,
                other_params=other_params,
            )

            # Register relationship
            rel_mgr.register_estimation(dev_est_id, epic_id, task_desc)

            return TransformationResult(
                success=True,
                entity=estimation,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            errors.append(
                TransformationError(
                    field_name="estimation",
                    message=f"Failed to transform estimation: {str(e)}",
                    severity="error",
                )
            )
            return TransformationResult(
                success=False,
                entity=None,
                errors=errors,
                warnings=warnings,
            )

    async def _transform_from_fields(
        self,
        extracted: ExtractedData,
        mapping: Dict[str, str],
        id_gen: IDGenerator,
        rel_mgr: RelationshipManager,
        position: int,
    ) -> TransformationResult[Estimation]:
        """Transform from field-based extraction (non-table)."""
        # Convert extracted fields to row format
        row = {}
        for field_name, field in extracted.fields.items():
            row[field_name] = field.value
        row.update(extracted.key_value_pairs)

        return await self.transform_row(row, mapping, id_gen, rel_mgr, position)

    async def transform_all_rows(
        self,
        extracted: ExtractedData,
        mapping: Dict[str, str],
        id_gen: IDGenerator,
        rel_mgr: RelationshipManager,
        epic_id: Optional[str] = None,
    ) -> List[TransformationResult[Estimation]]:
        """
        Transform all table rows to Estimation entities.

        Args:
            extracted: Extracted data with tables
            mapping: Field mapping
            id_gen: ID generator
            rel_mgr: Relationship manager
            epic_id: Optional epic ID to link all estimations to

        Returns:
            List of TransformationResults
        """
        results = []
        rows = self._get_table_rows(extracted)

        for i, row in enumerate(rows):
            result = await self.transform_row(
                row, mapping, id_gen, rel_mgr, i, epic_id
            )
            results.append(result)

        return results

    def _get_row_value(
        self,
        row: Dict[str, Any],
        mapping: Dict[str, str],
        target_field: str,
        fallback_keys: List[str] = None,
    ) -> Any:
        """Get value from row, trying mapping then fallback keys."""
        # Try mapping
        for src, tgt in mapping.items():
            if tgt == target_field and src in row:
                return row[src]

        # Try fallback keys
        if fallback_keys:
            for key in fallback_keys:
                if key in row:
                    return row[key]

        # Try target field name directly
        if target_field in row:
            return row[target_field]

        return None

    def _infer_domain(self, task_desc: str, row: Dict[str, Any]) -> str:
        """Infer domain from task description or row data."""
        task_lower = task_desc.lower()

        # Common domain keywords
        domain_keywords = {
            "PAY": ["payment", "pay", "transaction", "checkout", "billing"],
            "AUTH": ["auth", "login", "session", "jwt", "oauth", "sso", "mfa"],
            "ORD": ["order", "cart", "fulfillment", "shipping"],
            "CLM": ["claim", "edi", "adjudication", "eligibility"],
            "PRV": ["provider", "directory", "credential", "npi"],
            "NTF": ["notification", "email", "sms", "push", "alert"],
            "ANL": ["analytics", "dashboard", "report", "metric", "kpi"],
            "USR": ["user", "profile", "account", "member"],
            "API": ["api", "endpoint", "integration", "service"],
            "DB": ["database", "migration", "schema", "query"],
            "UI": ["frontend", "ui", "component", "page", "form"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in task_lower for kw in keywords):
                return domain

        # Check row for module hints
        module_hint = row.get("module") or row.get("Module") or row.get("area")
        if module_hint:
            return str(module_hint)[:4].upper()

        return "GEN"  # Generic

    def _collect_other_params(
        self, row: Dict[str, Any], mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Collect unmapped columns as other_params."""
        mapped_sources = set(mapping.keys())
        other = {}

        for key, value in row.items():
            if key not in mapped_sources and value is not None and value != "":
                other[key] = value

        return other
