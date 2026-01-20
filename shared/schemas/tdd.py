"""
TDD schema matching data/raw/tdds.csv exactly.

Columns: tdd_id, epic_id, dev_est_id, tdd_name, tdd_description, tdd_version,
         tdd_status, tdd_author, technical_components, design_decisions,
         tdd_dependencies, architecture_pattern, security_considerations,
         performance_requirements, created_at, updated_at
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class TDD(BaseModel):
    """Pydantic model for Technical Design Document entity matching tdds.csv schema."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
        },
    )

    # CSV column order for export
    CSV_COLUMNS: ClassVar[List[str]] = [
        "tdd_id",
        "epic_id",
        "dev_est_id",
        "tdd_name",
        "tdd_description",
        "tdd_version",
        "tdd_status",
        "tdd_author",
        "technical_components",
        "design_decisions",
        "tdd_dependencies",
        "architecture_pattern",
        "security_considerations",
        "performance_requirements",
        "created_at",
        "updated_at",
    ]

    # Primary key (format: TDD-NNN)
    tdd_id: str = Field(..., description="Primary key, format: TDD-NNN")

    # Foreign keys
    epic_id: str = Field(..., description="Foreign key to epics (format: EPIC-NNN)")
    dev_est_id: str = Field(..., description="Foreign key to estimations (format: EST-NNN)")

    # Basic fields
    tdd_name: str = Field(..., min_length=1, description="Name/title of the TDD")
    tdd_description: str = Field(..., min_length=1, description="Overview/summary of the design")
    tdd_version: str = Field(default="1.0", description="Version number (e.g., '1.0', '1.2')")

    # Status enum
    tdd_status: Literal["Draft", "In Review", "Approved"] = Field(
        default="Draft", description="TDD status"
    )

    # Author
    tdd_author: str = Field(..., description="Author email address")

    # JSON array fields (stored as string in CSV)
    technical_components: Union[List[str], str] = Field(
        default_factory=list, description="List of technologies/components used"
    )
    design_decisions: str = Field(
        default="", description="Key design decisions made"
    )
    tdd_dependencies: Union[List[str], str] = Field(
        default_factory=list, description="List of service/system dependencies"
    )

    # Technical details
    architecture_pattern: str = Field(
        default="", description="Architecture pattern (e.g., 'Adapter Pattern')"
    )
    security_considerations: str = Field(
        default="", description="Security requirements and considerations"
    )
    performance_requirements: str = Field(
        default="", description="Performance requirements and SLAs"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp",
    )

    @field_validator("tdd_id")
    @classmethod
    def validate_tdd_id(cls, v: str) -> str:
        """Validate tdd_id format: TDD-NNN."""
        if not re.match(r"^TDD-\d{3,}$", v):
            raise ValueError(f"tdd_id must match format TDD-NNN, got: {v}")
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

    @field_validator("tdd_author")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format for tdd_author."""
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_pattern, v):
            raise ValueError(f"tdd_author must be a valid email address, got: {v}")
        return v.lower()

    @field_validator("tdd_version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate and normalize version string."""
        # Accept formats: 1, 1.0, 1.0.0, v1.0, etc.
        v = v.strip().lstrip("v").lstrip("V")
        if not v:
            return "1.0"
        # If just a number, add .0
        if re.match(r"^\d+$", v):
            return f"{v}.0"
        return v

    @field_serializer("technical_components")
    def serialize_technical_components(self, value: Union[List[str], str]) -> str:
        """Serialize technical_components to JSON string."""
        if isinstance(value, str):
            return value
        return json.dumps(value)

    @field_serializer("tdd_dependencies")
    def serialize_tdd_dependencies(self, value: Union[List[str], str]) -> str:
        """Serialize tdd_dependencies to JSON string."""
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
        tdd_id: str,
        epic_id: str,
        dev_est_id: str,
        defaults: Optional[Dict[str, Any]] = None,
    ) -> "TDD":
        """
        Factory method to create TDD from extracted document data.

        Args:
            data: Dictionary of extracted field values
            tdd_id: Generated TDD ID
            epic_id: Foreign key to parent epic
            dev_est_id: Foreign key to estimation
            defaults: Optional default values for missing fields

        Returns:
            TDD instance
        """
        defaults = defaults or {}

        # Handle technical_components - could be list, string, or JSON string
        tech_components = data.get("technical_components") or []
        if isinstance(tech_components, str):
            try:
                tech_components = json.loads(tech_components)
            except json.JSONDecodeError:
                tech_components = [tech_components] if tech_components else []

        # Handle tdd_dependencies similarly
        dependencies = data.get("tdd_dependencies") or []
        if isinstance(dependencies, str):
            try:
                dependencies = json.loads(dependencies)
            except json.JSONDecodeError:
                dependencies = [dependencies] if dependencies else []

        return cls(
            tdd_id=tdd_id,
            epic_id=epic_id,
            dev_est_id=dev_est_id,
            tdd_name=data.get("tdd_name") or defaults.get("tdd_name", "Untitled TDD"),
            tdd_description=data.get("tdd_description")
            or defaults.get("tdd_description", "No description"),
            tdd_version=data.get("tdd_version") or "1.0",
            tdd_status=data.get("tdd_status") or defaults.get("tdd_status", "Draft"),
            tdd_author=data.get("tdd_author")
            or defaults.get("tdd_author", "unknown@company.com"),
            technical_components=tech_components,
            design_decisions=data.get("design_decisions") or "",
            tdd_dependencies=dependencies,
            architecture_pattern=data.get("architecture_pattern") or "",
            security_considerations=data.get("security_considerations") or "",
            performance_requirements=data.get("performance_requirements") or "",
            created_at=data.get("created_at") or datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def to_csv_row(self) -> Dict[str, Any]:
        """Convert to dictionary with CSV column ordering and serialization."""
        tech_components_str = (
            self.technical_components
            if isinstance(self.technical_components, str)
            else json.dumps(self.technical_components)
        )
        dependencies_str = (
            self.tdd_dependencies
            if isinstance(self.tdd_dependencies, str)
            else json.dumps(self.tdd_dependencies)
        )
        return {
            "tdd_id": self.tdd_id,
            "epic_id": self.epic_id,
            "dev_est_id": self.dev_est_id,
            "tdd_name": self.tdd_name,
            "tdd_description": self.tdd_description,
            "tdd_version": self.tdd_version,
            "tdd_status": self.tdd_status,
            "tdd_author": self.tdd_author,
            "technical_components": tech_components_str,
            "design_decisions": self.design_decisions,
            "tdd_dependencies": dependencies_str,
            "architecture_pattern": self.architecture_pattern,
            "security_considerations": self.security_considerations,
            "performance_requirements": self.performance_requirements,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }
