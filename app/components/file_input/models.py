"""Pydantic models for file-based input processing."""

from typing import Dict, List
from pydantic import BaseModel, Field, field_validator


class FileInputRequest(BaseModel):
    """Request to process a file through the pipeline."""

    file_path: str = Field(
        ...,
        description="Path to the input file (relative to backend root, e.g., 'input/new_req.txt')"
    )


class FileInputContent(BaseModel):
    """Schema for the JSON content inside the input file."""

    session_id: str | None = Field(
        default=None,
        description="Optional session identifier (auto-generated if not provided)"
    )
    requirement_text: str = Field(
        ...,
        min_length=10,
        description="The requirement or epic description to analyze"
    )
    jira_epic_id: str | None = Field(
        default=None,
        description="Optional Jira epic ID for traceability"
    )
    selected_matches: List[Dict] = Field(
        default_factory=list,
        description="Pre-selected matches (empty list = auto-select top 5)"
    )

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str | None) -> str | None:
        """Ensure session_id contains only safe characters if provided."""
        if v is None:
            return v
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("session_id must contain only alphanumeric, underscore, or hyphen characters")
        return v


class FileProcessingResponse(BaseModel):
    """Response from file processing endpoint."""

    session_id: str = Field(..., description="The session ID from the processed file")
    status: str = Field(..., description="Pipeline completion status")
    output_path: str = Field(..., description="Path to the session output directory")
    message: str = Field(..., description="Human-readable status message")
    error_message: str | None = Field(default=None, description="Error details if failed")
