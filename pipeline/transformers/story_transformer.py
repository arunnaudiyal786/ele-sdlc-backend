"""
Story entity transformer.

Transforms extracted document data to Story schema.
Handles multiple stories per document (common for story documents).
"""

from datetime import date
from typing import Any, Dict, List, Optional, Type

from pipeline.core.id_generator import IDGenerator
from pipeline.core.relationship_manager import RelationshipManager
from pipeline.extractors.base import ExtractedData
from pipeline.transformers.base import BaseTransformer, TransformationError, TransformationResult
from pipeline.transformers.normalizers import (
    array_to_json_string,
    clean_text,
    date_normalizer,
    dict_to_json_string,
    email_normalizer,
    enum_normalizer,
    number_normalizer,
)
from shared.schemas.story import Story


class StoryTransformer(BaseTransformer[Story]):
    """
    Transforms extracted data to Story entities.

    Handles:
    - Multiple stories per document
    - Jira ID preservation or generation
    - Acceptance criteria formatting
    - Full relationship linking
    """

    def get_target_schema(self) -> Type[Story]:
        return Story

    async def transform(
        self,
        extracted: ExtractedData,
        mapping: Dict[str, str],
        id_gen: IDGenerator,
        rel_mgr: RelationshipManager,
        position: int = 0,
    ) -> TransformationResult[Story]:
        """
        Transform a single extraction to Story entity.

        For documents with multiple stories in tables, use transform_all().
        """
        # If extraction has tables, transform first row
        rows = self._get_table_rows(extracted)
        if rows:
            return await self.transform_row(
                rows[0], mapping, id_gen, rel_mgr, position
            )

        # No table - use fields directly
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
        dev_est_id: Optional[str] = None,
        tdd_id: Optional[str] = None,
    ) -> TransformationResult[Story]:
        """
        Transform a single table row to Story entity.

        Args:
            row: Row dictionary from extraction
            mapping: Field mapping
            id_gen: ID generator
            rel_mgr: Relationship manager
            position: Position index
            epic_id, dev_est_id, tdd_id: Optional explicit parent IDs

        Returns:
            TransformationResult with Story
        """
        errors = []
        warnings = []

        try:
            # Get or generate Jira story ID
            existing_jira_id = self._get_row_value(
                row, mapping, "jira_story_id",
                fallback_keys=["jira_id", "id", "ticket", "Jira ID", "Story ID", "Key"]
            )
            jira_story_id = id_gen.generate_story_id(existing_jira_id)

            # Resolve parent IDs
            if not epic_id:
                epic_id = rel_mgr.get_epic_by_position(position)
            if not epic_id:
                epic_id = rel_mgr.get_epic_by_position(0)
            if not epic_id:
                epic_id = id_gen.generate_epic_id()
                rel_mgr.register_epic(epic_id, f"auto_epic_story_{position}")
                warnings.append(
                    TransformationError(
                        field_name="epic_id",
                        message="No epic found, generated placeholder",
                        severity="warning",
                    )
                )

            if not dev_est_id:
                dev_est_id = rel_mgr.get_estimation_for_epic(epic_id)
            if not dev_est_id:
                dev_est_id = rel_mgr.get_estimation_by_position(position)
            if not dev_est_id:
                dev_est_id = id_gen.generate_estimation_id()
                rel_mgr.register_estimation(dev_est_id, epic_id, f"auto_est_story_{position}")
                warnings.append(
                    TransformationError(
                        field_name="dev_est_id",
                        message="No estimation found, generated placeholder",
                        severity="warning",
                    )
                )

            if not tdd_id:
                tdd_id = rel_mgr.get_tdd_for_epic(epic_id)
            if not tdd_id:
                tdd_id = rel_mgr.get_tdd_by_position(position)
            if not tdd_id:
                tdd_id = id_gen.generate_tdd_id()
                rel_mgr.register_tdd(tdd_id, epic_id, dev_est_id, f"auto_tdd_story_{position}")
                warnings.append(
                    TransformationError(
                        field_name="tdd_id",
                        message="No TDD found, generated placeholder",
                        severity="warning",
                    )
                )

            # Issue type
            issue_type = self._get_row_value(
                row, mapping, "issue_type",
                fallback_keys=["type", "Type", "Issue Type"]
            )
            issue_type = enum_normalizer(
                issue_type,
                ["Story", "Task", "Sub-task", "Bug"],
                default="Story"
            )

            # Summary
            summary = self._get_row_value(
                row, mapping, "summary",
                fallback_keys=["title", "Summary", "Title", "Name"]
            )
            summary = clean_text(summary) or f"Story {position + 1}"

            # Description
            description = self._get_row_value(
                row, mapping, "description",
                fallback_keys=["desc", "Description", "Details"]
            )
            description = clean_text(description) or ""

            # Assignee
            assignee = self._get_row_value(
                row, mapping, "assignee",
                fallback_keys=["assigned_to", "owner", "Assignee", "Assigned To"]
            )
            assignee = email_normalizer(assignee) or ""

            # Status
            status = self._get_row_value(
                row, mapping, "status",
                fallback_keys=["Status", "state", "State"]
            )
            status = enum_normalizer(
                status,
                ["To Do", "In Progress", "Done", "Blocked"],
                default="To Do"
            )

            # Story points
            story_points = self._get_row_value(
                row, mapping, "story_points",
                fallback_keys=["points", "sp", "Story Points", "SP", "Estimate"]
            )
            story_points = number_normalizer(story_points, 0.0)

            # Sprint
            sprint = self._get_row_value(
                row, mapping, "sprint",
                fallback_keys=["Sprint", "iteration", "Iteration"]
            )
            sprint = clean_text(sprint) or ""

            # Priority
            priority = self._get_row_value(
                row, mapping, "priority",
                fallback_keys=["Priority", "prio"]
            )
            priority = enum_normalizer(
                priority,
                ["Critical", "High", "Medium", "Low"],
                default="Medium"
            )

            # Labels
            labels = self._get_row_value(
                row, mapping, "labels",
                fallback_keys=["Labels", "tags", "Tags"]
            )
            if labels:
                if isinstance(labels, str):
                    if labels.startswith("["):
                        import json
                        try:
                            labels = json.loads(labels)
                        except json.JSONDecodeError:
                            labels = [l.strip() for l in labels.split(",")]
                    else:
                        labels = [l.strip() for l in labels.split(",") if l.strip()]
                elif not isinstance(labels, list):
                    labels = [str(labels)]
            else:
                labels = []

            # Acceptance criteria
            acceptance_criteria = self._get_row_value(
                row, mapping, "acceptance_criteria",
                fallback_keys=["ac", "criteria", "Acceptance Criteria", "AC"]
            )
            acceptance_criteria = self._format_acceptance_criteria(acceptance_criteria)

            # Dates
            created_date = self._get_row_value(
                row, mapping, "story_created_date",
                fallback_keys=["created", "Created", "Created Date"]
            )
            created_date = date_normalizer(created_date)

            updated_date = self._get_row_value(
                row, mapping, "story_updated_date",
                fallback_keys=["updated", "Updated", "Updated Date"]
            )
            updated_date = date_normalizer(updated_date)

            # Other params
            other_params = self._collect_other_params(row, mapping)

            # Create Story entity
            story = Story(
                jira_story_id=jira_story_id,
                dev_est_id=dev_est_id,
                epic_id=epic_id,
                tdd_id=tdd_id,
                issue_type=issue_type,
                summary=summary,
                description=description,
                assignee=assignee,
                status=status,
                story_points=story_points,
                sprint=sprint,
                priority=priority,
                labels=labels,
                acceptance_criteria=acceptance_criteria,
                story_created_date=created_date,
                story_updated_date=updated_date,
                other_params=other_params,
            )

            # Register relationship
            rel_mgr.register_story(
                jira_story_id, epic_id, dev_est_id, tdd_id, summary
            )

            return TransformationResult(
                success=True,
                entity=story,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            errors.append(
                TransformationError(
                    field_name="story",
                    message=f"Failed to transform story: {str(e)}",
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
    ) -> TransformationResult[Story]:
        """Transform from field-based extraction."""
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
        dev_est_id: Optional[str] = None,
        tdd_id: Optional[str] = None,
    ) -> List[TransformationResult[Story]]:
        """
        Transform all table rows to Story entities.

        Args:
            extracted: Extracted data with tables
            mapping: Field mapping
            id_gen: ID generator
            rel_mgr: Relationship manager
            epic_id, dev_est_id, tdd_id: Optional parent IDs for all stories

        Returns:
            List of TransformationResults
        """
        results = []
        rows = self._get_table_rows(extracted)

        for i, row in enumerate(rows):
            result = await self.transform_row(
                row, mapping, id_gen, rel_mgr, i,
                epic_id, dev_est_id, tdd_id
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
        for src, tgt in mapping.items():
            if tgt == target_field and src in row:
                return row[src]

        if fallback_keys:
            for key in fallback_keys:
                if key in row:
                    return row[key]

        if target_field in row:
            return row[target_field]

        return None

    def _format_acceptance_criteria(self, value: Any) -> str:
        """Format acceptance criteria consistently."""
        if not value:
            return ""

        if isinstance(value, list):
            # Number the criteria
            lines = [f"{i+1}. {item}" for i, item in enumerate(value)]
            return "\n".join(lines)

        if isinstance(value, str):
            value = value.strip()
            # If it's JSON, parse it
            if value.startswith("["):
                import json
                try:
                    items = json.loads(value)
                    if isinstance(items, list):
                        lines = [f"{i+1}. {item}" for i, item in enumerate(items)]
                        return "\n".join(lines)
                except json.JSONDecodeError:
                    pass

            # Clean up existing formatting
            return clean_text(value)

        return str(value)

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
