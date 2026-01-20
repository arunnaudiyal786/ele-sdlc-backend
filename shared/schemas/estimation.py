"""
Estimation schema matching data/raw/estimations.csv exactly.

Columns: dev_est_id, epic_id, module_id, task_description, complexity,
         dev_effort_hours, qa_effort_hours, total_effort_hours, total_story_points,
         risk_level, estimation_method, confidence_level, estimated_by,
         estimation_date, other_params
"""

import json
import re
from datetime import date, datetime, timezone
from typing import Any, ClassVar, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator


class Estimation(BaseModel):
    """Pydantic model for Estimation entity matching estimations.csv schema."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None,
        },
    )

    # CSV column order for export
    CSV_COLUMNS: ClassVar[List[str]] = [
        "dev_est_id",
        "epic_id",
        "module_id",
        "task_description",
        "complexity",
        "dev_effort_hours",
        "qa_effort_hours",
        "total_effort_hours",
        "total_story_points",
        "risk_level",
        "estimation_method",
        "confidence_level",
        "estimated_by",
        "estimation_date",
        "other_params",
    ]

    # Primary key (format: EST-NNN)
    dev_est_id: str = Field(..., description="Primary key, format: EST-NNN")

    # Foreign key to epics
    epic_id: str = Field(..., description="Foreign key to epics (format: EPIC-NNN)")

    # Module identifier
    module_id: str = Field(..., description="Module ID (format: MOD-{DOMAIN}-NNN)")

    # Task details
    task_description: str = Field(..., min_length=1, description="Description of the task/module")

    # Complexity enum
    complexity: Literal["Small", "Medium", "Large"] = Field(
        default="Medium", description="Task complexity"
    )

    # Effort hours
    dev_effort_hours: float = Field(default=0.0, ge=0, description="Development hours")
    qa_effort_hours: float = Field(default=0.0, ge=0, description="QA/testing hours")
    total_effort_hours: float = Field(
        default=0.0, ge=0, description="Total hours (calculated: dev + qa)"
    )

    # Story points
    total_story_points: int = Field(default=0, ge=0, description="Total story points")

    # Risk and confidence
    risk_level: Literal["Low", "Medium", "High"] = Field(
        default="Medium", description="Risk level"
    )
    estimation_method: str = Field(
        default="Planning Poker", description="Method used for estimation"
    )
    confidence_level: Literal["Low", "Medium", "High"] = Field(
        default="Medium", description="Confidence in the estimate"
    )

    # Estimator info
    estimated_by: str = Field(..., description="Email of the person who created the estimate")
    estimation_date: Optional[date] = Field(None, description="Date estimate was created")

    # Additional parameters (stored as JSON string)
    other_params: Union[Dict[str, Any], str] = Field(
        default_factory=dict, description="Additional parameters as JSON"
    )

    @field_validator("dev_est_id")
    @classmethod
    def validate_dev_est_id(cls, v: str) -> str:
        """Validate dev_est_id format: EST-NNN."""
        if not re.match(r"^EST-\d{3,}$", v):
            raise ValueError(f"dev_est_id must match format EST-NNN, got: {v}")
        return v

    @field_validator("epic_id")
    @classmethod
    def validate_epic_id(cls, v: str) -> str:
        """Validate epic_id format: EPIC-NNN."""
        if not re.match(r"^EPIC-\d{3,}$", v):
            raise ValueError(f"epic_id must match format EPIC-NNN, got: {v}")
        return v

    @field_validator("module_id")
    @classmethod
    def validate_module_id(cls, v: str) -> str:
        """Validate module_id format: MOD-{DOMAIN}-NNN."""
        if not re.match(r"^MOD-[A-Z]{2,}-\d{3,}$", v):
            raise ValueError(f"module_id must match format MOD-XXX-NNN, got: {v}")
        return v

    @field_validator("estimated_by")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format for estimated_by."""
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_pattern, v):
            raise ValueError(f"estimated_by must be a valid email address, got: {v}")
        return v.lower()

    @model_validator(mode="after")
    def calculate_total_hours(self) -> "Estimation":
        """Auto-calculate total_effort_hours if not explicitly set or zero."""
        calculated = self.dev_effort_hours + self.qa_effort_hours
        if self.total_effort_hours == 0 and calculated > 0:
            self.total_effort_hours = calculated
        return self

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
        dev_est_id: str,
        epic_id: str,
        module_id: str,
        defaults: Optional[Dict[str, Any]] = None,
    ) -> "Estimation":
        """
        Factory method to create Estimation from extracted document data.

        Args:
            data: Dictionary of extracted field values
            dev_est_id: Generated estimation ID
            epic_id: Foreign key to parent epic
            module_id: Generated module ID
            defaults: Optional default values for missing fields

        Returns:
            Estimation instance
        """
        defaults = defaults or {}

        return cls(
            dev_est_id=dev_est_id,
            epic_id=epic_id,
            module_id=module_id,
            task_description=data.get("task_description")
            or defaults.get("task_description", "No description"),
            complexity=data.get("complexity") or defaults.get("complexity", "Medium"),
            dev_effort_hours=float(data.get("dev_effort_hours") or 0),
            qa_effort_hours=float(data.get("qa_effort_hours") or 0),
            total_effort_hours=float(data.get("total_effort_hours") or 0),
            total_story_points=int(data.get("total_story_points") or 0),
            risk_level=data.get("risk_level") or defaults.get("risk_level", "Medium"),
            estimation_method=data.get("estimation_method")
            or defaults.get("estimation_method", "Planning Poker"),
            confidence_level=data.get("confidence_level")
            or defaults.get("confidence_level", "Medium"),
            estimated_by=data.get("estimated_by")
            or defaults.get("estimated_by", "unknown@company.com"),
            estimation_date=data.get("estimation_date"),
            other_params=data.get("other_params") or {},
        )

    def to_csv_row(self) -> Dict[str, Any]:
        """Convert to dictionary with CSV column ordering and serialization."""
        other_params_str = (
            self.other_params
            if isinstance(self.other_params, str)
            else json.dumps(self.other_params)
        )
        return {
            "dev_est_id": self.dev_est_id,
            "epic_id": self.epic_id,
            "module_id": self.module_id,
            "task_description": self.task_description,
            "complexity": self.complexity,
            "dev_effort_hours": self.dev_effort_hours,
            "qa_effort_hours": self.qa_effort_hours,
            "total_effort_hours": self.total_effort_hours,
            "total_story_points": self.total_story_points,
            "risk_level": self.risk_level,
            "estimation_method": self.estimation_method,
            "confidence_level": self.confidence_level,
            "estimated_by": self.estimated_by,
            "estimation_date": (
                self.estimation_date.isoformat() if self.estimation_date else ""
            ),
            "other_params": other_params_str,
        }
