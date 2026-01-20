"""
Epic schema matching data/raw/epics.csv exactly.

Columns: epic_id, epic_name, req_id, jira_id, req_description, status,
         epic_priority, epic_owner, epic_team, epic_start_date, epic_target_date,
         created_at, updated_at
"""

import re
from datetime import date, datetime, timezone
from typing import Any, ClassVar, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class Epic(BaseModel):
    """Pydantic model for Epic entity matching epics.csv schema."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None,
        },
    )

    # CSV column order for export
    CSV_COLUMNS: ClassVar[List[str]] = [
        "epic_id",
        "epic_name",
        "req_id",
        "jira_id",
        "req_description",
        "status",
        "epic_priority",
        "epic_owner",
        "epic_team",
        "epic_start_date",
        "epic_target_date",
        "created_at",
        "updated_at",
    ]

    # Primary key (format: EPIC-NNN)
    epic_id: str = Field(..., description="Primary key, format: EPIC-NNN")

    # Basic fields
    epic_name: str = Field(..., min_length=1, description="Name of the epic/initiative")
    req_id: Optional[str] = Field(None, description="Requirement ID (e.g., REQ-2025-001)")
    jira_id: Optional[str] = Field(None, description="Jira epic ID (e.g., MM16783)")
    req_description: str = Field(
        ..., min_length=1, description="Full description of the requirement"
    )

    # Status and priority enums
    status: Literal["Planning", "In Progress", "Done", "Blocked"] = Field(
        default="Planning", description="Current status of the epic"
    )
    epic_priority: Literal["Critical", "High", "Medium", "Low"] = Field(
        default="Medium", description="Priority level"
    )

    # Owner and team
    epic_owner: str = Field(..., description="Owner email address")
    epic_team: str = Field(..., description="Team name (e.g., Commerce, Platform)")

    # Dates
    epic_start_date: Optional[date] = Field(None, description="Start date (ISO format)")
    epic_target_date: Optional[date] = Field(None, description="Target completion date")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp",
    )

    @field_validator("epic_id")
    @classmethod
    def validate_epic_id(cls, v: str) -> str:
        """Validate epic_id format: EPIC-NNN."""
        if not re.match(r"^EPIC-\d{3,}$", v):
            raise ValueError(f"epic_id must match format EPIC-NNN, got: {v}")
        return v

    @field_validator("epic_owner")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format for epic_owner."""
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_pattern, v):
            raise ValueError(f"epic_owner must be a valid email address, got: {v}")
        return v.lower()

    @field_validator("jira_id")
    @classmethod
    def validate_jira_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate Jira ID format if provided."""
        if v is None:
            return v
        # Accept formats: MM16783, PROJ-123, ABC-1234
        if not re.match(r"^(MM\d+|[A-Z]+-\d+)$", v):
            raise ValueError(f"jira_id must match format MM##### or PROJ-###, got: {v}")
        return v

    @classmethod
    def csv_columns(cls) -> List[str]:
        """Return ordered list of CSV columns."""
        return cls.CSV_COLUMNS.copy()

    @classmethod
    def from_extracted_data(
        cls,
        data: Dict[str, Any],
        epic_id: str,
        defaults: Optional[Dict[str, Any]] = None,
    ) -> "Epic":
        """
        Factory method to create Epic from extracted document data.

        Args:
            data: Dictionary of extracted field values
            epic_id: Generated epic ID
            defaults: Optional default values for missing fields

        Returns:
            Epic instance
        """
        defaults = defaults or {}

        # Map extracted data to model fields with fallbacks
        return cls(
            epic_id=epic_id,
            epic_name=data.get("epic_name") or defaults.get("epic_name", "Untitled Epic"),
            req_id=data.get("req_id"),
            jira_id=data.get("jira_id"),
            req_description=data.get("req_description")
            or defaults.get("req_description", "No description provided"),
            status=data.get("status") or defaults.get("status", "Planning"),
            epic_priority=data.get("epic_priority")
            or defaults.get("epic_priority", "Medium"),
            epic_owner=data.get("epic_owner")
            or defaults.get("epic_owner", "unknown@company.com"),
            epic_team=data.get("epic_team") or defaults.get("epic_team", "Unknown"),
            epic_start_date=data.get("epic_start_date"),
            epic_target_date=data.get("epic_target_date"),
            created_at=data.get("created_at") or datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def to_csv_row(self) -> Dict[str, Any]:
        """Convert to dictionary with CSV column ordering and serialization."""
        return {
            "epic_id": self.epic_id,
            "epic_name": self.epic_name,
            "req_id": self.req_id or "",
            "jira_id": self.jira_id or "",
            "req_description": self.req_description,
            "status": self.status,
            "epic_priority": self.epic_priority,
            "epic_owner": self.epic_owner,
            "epic_team": self.epic_team,
            "epic_start_date": self.epic_start_date.isoformat() if self.epic_start_date else "",
            "epic_target_date": (
                self.epic_target_date.isoformat() if self.epic_target_date else ""
            ),
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }
