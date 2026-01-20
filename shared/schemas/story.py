"""
Story schema matching data/raw/stories_tasks.csv exactly.

Columns: jira_story_id, dev_est_id, epic_id, tdd_id, issue_type, summary,
         description, assignee, status, story_points, sprint, priority,
         labels, acceptance_criteria, story_created_date, story_updated_date,
         other_params
"""

import json
import re
from datetime import date, datetime, timezone
from typing import Any, ClassVar, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class Story(BaseModel):
    """Pydantic model for Story/Task entity matching stories_tasks.csv schema."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None,
        },
    )

    # CSV column order for export
    CSV_COLUMNS: ClassVar[List[str]] = [
        "jira_story_id",
        "dev_est_id",
        "epic_id",
        "tdd_id",
        "issue_type",
        "summary",
        "description",
        "assignee",
        "status",
        "story_points",
        "sprint",
        "priority",
        "labels",
        "acceptance_criteria",
        "story_created_date",
        "story_updated_date",
        "other_params",
    ]

    # Primary key (e.g., "MMO-12323" or generated "STORY-NNN")
    jira_story_id: str = Field(..., description="Primary key, Jira ID or STORY-NNN")

    # Foreign keys
    dev_est_id: str = Field(..., description="Foreign key to estimations (format: EST-NNN)")
    epic_id: str = Field(..., description="Foreign key to epics (format: EPIC-NNN)")
    tdd_id: str = Field(..., description="Foreign key to TDDs (format: TDD-NNN)")

    # Issue details
    issue_type: Literal["Story", "Task", "Sub-task", "Bug"] = Field(
        default="Story", description="Type of the issue"
    )
    summary: str = Field(..., min_length=1, description="Story/task title/summary")
    description: str = Field(default="", description="Detailed description")

    # Assignment
    assignee: str = Field(default="", description="Assigned person email")

    # Status and priority
    status: Literal["To Do", "In Progress", "Done", "Blocked"] = Field(
        default="To Do", description="Current status"
    )
    story_points: float = Field(default=0.0, ge=0, description="Story points")
    sprint: str = Field(default="", description="Sprint name (e.g., 'Sprint-25')")
    priority: Literal["Critical", "High", "Medium", "Low"] = Field(
        default="Medium", description="Priority level"
    )

    # Labels (stored as JSON array string)
    labels: Union[List[str], str] = Field(
        default_factory=list, description="List of labels/tags"
    )

    # Acceptance criteria
    acceptance_criteria: str = Field(
        default="", description="Acceptance criteria (can be multi-line)"
    )

    # Dates
    story_created_date: Optional[date] = Field(None, description="Creation date")
    story_updated_date: Optional[date] = Field(None, description="Last update date")

    # Additional parameters (stored as JSON string)
    other_params: Union[Dict[str, Any], str] = Field(
        default_factory=dict, description="Additional parameters as JSON"
    )

    @field_validator("jira_story_id")
    @classmethod
    def validate_jira_story_id(cls, v: str) -> str:
        """Validate jira_story_id format."""
        # Accept: MMO-12323, PROJ-123, STORY-001, or MM##### patterns
        valid_patterns = [
            r"^[A-Z]+-\d+$",  # PROJ-123
            r"^MM\d+$",  # MM12345
            r"^STORY-\d{3,}$",  # STORY-001
        ]
        if not any(re.match(pattern, v) for pattern in valid_patterns):
            raise ValueError(
                f"jira_story_id must match format PROJ-###, MM#####, or STORY-NNN, got: {v}"
            )
        return v

    @field_validator("epic_id")
    @classmethod
    def validate_epic_id(cls, v: str) -> str:
        """Validate epic_id format: EPIC-NNN."""
        if not re.match(r"^EPIC-\d{3,}$", v):
            raise ValueError(f"epic_id must match format EPIC-NNN, got: {v}")
        return v

    @field_validator("dev_est_id")
    @classmethod
    def validate_dev_est_id(cls, v: str) -> str:
        """Validate dev_est_id format: EST-NNN."""
        if not re.match(r"^EST-\d{3,}$", v):
            raise ValueError(f"dev_est_id must match format EST-NNN, got: {v}")
        return v

    @field_validator("tdd_id")
    @classmethod
    def validate_tdd_id(cls, v: str) -> str:
        """Validate tdd_id format: TDD-NNN."""
        if not re.match(r"^TDD-\d{3,}$", v):
            raise ValueError(f"tdd_id must match format TDD-NNN, got: {v}")
        return v

    @field_validator("assignee")
    @classmethod
    def validate_assignee_email(cls, v: str) -> str:
        """Validate email format for assignee if provided."""
        if not v:
            return v
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_pattern, v):
            raise ValueError(f"assignee must be a valid email address, got: {v}")
        return v.lower()

    @field_serializer("labels")
    def serialize_labels(self, value: Union[List[str], str]) -> str:
        """Serialize labels to JSON string."""
        if isinstance(value, str):
            return value
        return json.dumps(value)

    @field_serializer("other_params")
    def serialize_other_params(self, value: Union[Dict[str, Any], str]) -> str:
        """Serialize other_params to JSON string."""
        if isinstance(value, str):
            return value
        return json.dumps(value)

    @classmethod
    def csv_columns(cls) -> List[str]:
        """Return ordered list of CSV columns."""
        return cls.CSV_COLUMNS.copy()

    @classmethod
    def from_extracted_data(
        cls,
        data: Dict[str, Any],
        jira_story_id: str,
        dev_est_id: str,
        epic_id: str,
        tdd_id: str,
        defaults: Optional[Dict[str, Any]] = None,
    ) -> "Story":
        """
        Factory method to create Story from extracted document data.

        Args:
            data: Dictionary of extracted field values
            jira_story_id: Jira ID or generated story ID
            dev_est_id: Foreign key to estimation
            epic_id: Foreign key to epic
            tdd_id: Foreign key to TDD
            defaults: Optional default values for missing fields

        Returns:
            Story instance
        """
        defaults = defaults or {}

        # Handle labels - could be list, string, or JSON string
        labels = data.get("labels") or []
        if isinstance(labels, str):
            try:
                labels = json.loads(labels)
            except json.JSONDecodeError:
                # If it's a comma-separated string, split it
                labels = [l.strip() for l in labels.split(",") if l.strip()]

        return cls(
            jira_story_id=jira_story_id,
            dev_est_id=dev_est_id,
            epic_id=epic_id,
            tdd_id=tdd_id,
            issue_type=data.get("issue_type") or defaults.get("issue_type", "Story"),
            summary=data.get("summary") or defaults.get("summary", "Untitled Story"),
            description=data.get("description") or "",
            assignee=data.get("assignee") or "",
            status=data.get("status") or defaults.get("status", "To Do"),
            story_points=float(data.get("story_points") or 0),
            sprint=data.get("sprint") or "",
            priority=data.get("priority") or defaults.get("priority", "Medium"),
            labels=labels,
            acceptance_criteria=data.get("acceptance_criteria") or "",
            story_created_date=data.get("story_created_date"),
            story_updated_date=data.get("story_updated_date"),
            other_params=data.get("other_params") or {},
        )

    def to_csv_row(self) -> Dict[str, Any]:
        """Convert to dictionary with CSV column ordering and serialization."""
        labels_str = (
            self.labels if isinstance(self.labels, str) else json.dumps(self.labels)
        )
        other_params_str = (
            self.other_params
            if isinstance(self.other_params, str)
            else json.dumps(self.other_params)
        )
        return {
            "jira_story_id": self.jira_story_id,
            "dev_est_id": self.dev_est_id,
            "epic_id": self.epic_id,
            "tdd_id": self.tdd_id,
            "issue_type": self.issue_type,
            "summary": self.summary,
            "description": self.description,
            "assignee": self.assignee,
            "status": self.status,
            "story_points": self.story_points,
            "sprint": self.sprint,
            "priority": self.priority,
            "labels": labels_str,
            "acceptance_criteria": self.acceptance_criteria,
            "story_created_date": (
                self.story_created_date.isoformat() if self.story_created_date else ""
            ),
            "story_updated_date": (
                self.story_updated_date.isoformat() if self.story_updated_date else ""
            ),
            "other_params": other_params_str,
        }
