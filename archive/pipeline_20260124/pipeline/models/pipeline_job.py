"""
Pipeline job tracking models.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Pipeline job status states."""

    CREATED = "created"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    MAPPING = "mapping"
    MAPPED = "mapped"
    TRANSFORMING = "transforming"
    TRANSFORMED = "transformed"
    VALIDATING = "validating"
    VALIDATED = "validated"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStep(str, Enum):
    """Pipeline processing steps."""

    UPLOAD = "upload"
    EXTRACT = "extract"
    MAP = "map"
    TRANSFORM = "transform"
    VALIDATE = "validate"
    EXPORT = "export"


class FileInfo(BaseModel):
    """Information about an uploaded file in a job."""

    filename: str
    file_path: str
    file_size: int
    document_type: str
    uploaded_at: datetime


class PipelineJob(BaseModel):
    """Model for tracking a pipeline processing job."""

    job_id: str = Field(..., description="Unique job identifier (JOB-YYYYMMDD-NNN)")
    job_type: str = Field(default="interactive", description="interactive or batch")
    status: JobStatus = Field(default=JobStatus.CREATED)
    current_step: Optional[JobStep] = Field(None, description="Current processing step")
    steps_completed: List[JobStep] = Field(default_factory=list)

    # Files
    files_uploaded: List[FileInfo] = Field(default_factory=list)

    # Processing metadata
    extraction_results: Optional[Dict[str, Any]] = Field(None)
    mapping_results: Optional[Dict[str, Any]] = Field(None)
    transformation_results: Optional[Dict[str, Any]] = Field(None)
    validation_results: Optional[Dict[str, Any]] = Field(None)
    export_results: Optional[Dict[str, Any]] = Field(None)

    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(None)

    # Error handling
    error_message: Optional[str] = Field(None)
    warnings: List[str] = Field(default_factory=list)

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def mark_step_completed(self, step: JobStep) -> None:
        """Mark a step as completed."""
        if step not in self.steps_completed:
            self.steps_completed.append(step)
        self.updated_at = datetime.now(timezone.utc)

    def update_status(self, status: JobStatus) -> None:
        """Update job status."""
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
        if status == JobStatus.COMPLETED:
            self.completed_at = datetime.now(timezone.utc)

    def set_error(self, message: str) -> None:
        """Set error and update status to failed."""
        self.error_message = message
        self.status = JobStatus.FAILED
        self.updated_at = datetime.now(timezone.utc)
