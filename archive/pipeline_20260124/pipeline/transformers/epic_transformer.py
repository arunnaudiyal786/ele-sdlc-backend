"""
Epic entity transformer.

Transforms extracted document data to Epic schema.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Type

from pipeline.core.id_generator import IDGenerator
from pipeline.core.relationship_manager import RelationshipManager
from pipeline.extractors.base import ExtractedData
from pipeline.transformers.base import BaseTransformer, TransformationError, TransformationResult
from pipeline.transformers.normalizers import (
    clean_text,
    date_normalizer,
    email_normalizer,
    enum_normalizer,
)
from shared.schemas.epic import Epic


class EpicTransformer(BaseTransformer[Epic]):
    """
    Transforms extracted data to Epic entities.

    Handles:
    - ID generation
    - Field mapping and normalization
    - Relationship registration
    """

    def get_target_schema(self) -> Type[Epic]:
        return Epic

    async def transform(
        self,
        extracted: ExtractedData,
        mapping: Dict[str, str],
        id_gen: IDGenerator,
        rel_mgr: RelationshipManager,
        position: int = 0,
    ) -> TransformationResult[Epic]:
        """
        Transform extracted data to Epic entity.

        Args:
            extracted: Extracted document data
            mapping: Field mapping from source to target
            id_gen: ID generator
            rel_mgr: Relationship manager
            position: Position for ordering

        Returns:
            TransformationResult with Epic entity or errors
        """
        errors = []
        warnings = []

        # Generate epic ID
        epic_id = id_gen.generate_epic_id()

        # Extract and normalize fields
        try:
            # Required fields
            epic_name = self._get_mapped_value(
                extracted, mapping, "epic_name",
                default=f"Epic {position + 1}"
            )
            epic_name = clean_text(epic_name)

            req_description = self._get_mapped_value(
                extracted, mapping, "req_description",
                default=extracted.raw_content[:500] if extracted.raw_content else "No description"
            )
            req_description = clean_text(req_description)

            # Owner - try various sources
            epic_owner = self._get_mapped_value(extracted, mapping, "epic_owner")
            if not epic_owner and extracted.emails:
                epic_owner = extracted.emails[0]
            epic_owner = email_normalizer(epic_owner) or "unknown@company.com"

            # Team
            epic_team = self._get_mapped_value(
                extracted, mapping, "epic_team", default="Unknown"
            )
            epic_team = clean_text(epic_team) or "Unknown"

            # Optional fields with normalization
            req_id = self._get_mapped_value(extracted, mapping, "req_id")

            # Jira ID - try mapped value or detected patterns
            jira_id = self._get_mapped_value(extracted, mapping, "jira_id")
            if not jira_id and extracted.jira_ids:
                # Use first detected Jira ID that looks like an epic
                for jid in extracted.jira_ids:
                    if jid.startswith("MM") or "-" in jid:
                        jira_id = jid
                        break

            # Enums
            status = self._get_mapped_value(extracted, mapping, "status")
            status = enum_normalizer(
                status,
                ["Planning", "In Progress", "Done", "Blocked"],
                default="Planning"
            )

            priority = self._get_mapped_value(extracted, mapping, "epic_priority")
            priority = enum_normalizer(
                priority,
                ["Critical", "High", "Medium", "Low"],
                default="Medium"
            )

            # Dates
            start_date = self._get_mapped_value(extracted, mapping, "epic_start_date")
            start_date = date_normalizer(start_date)

            target_date = self._get_mapped_value(extracted, mapping, "epic_target_date")
            target_date = date_normalizer(target_date)
            if not target_date and extracted.dates:
                # Try to use first detected date as target
                target_date = date_normalizer(extracted.dates[0])

            # Create Epic entity
            epic = Epic(
                epic_id=epic_id,
                epic_name=epic_name,
                req_id=req_id,
                jira_id=jira_id,
                req_description=req_description,
                status=status,
                epic_priority=priority,
                epic_owner=epic_owner,
                epic_team=epic_team,
                epic_start_date=start_date,
                epic_target_date=target_date,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            # Register in relationship manager
            source_identifier = jira_id or epic_name
            rel_mgr.register_epic(epic_id, source_identifier)

            return TransformationResult(
                success=True,
                entity=epic,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            errors.append(
                TransformationError(
                    field_name="epic",
                    message=f"Failed to transform epic: {str(e)}",
                    severity="error",
                )
            )
            return TransformationResult(
                success=False,
                entity=None,
                errors=errors,
                warnings=warnings,
            )
