"""
API request/response models for the pipeline endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from pipeline.models.pipeline_job import JobStatus


class UploadResponse(BaseModel):
    """Response from file upload endpoint."""

    job_id: str = Field(..., description="Generated job ID")
    status: str = Field(default="uploaded")
    files_received: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of files with filename, size, type"
    )
    message: str = Field(default="Files uploaded successfully")


class ExtractRequest(BaseModel):
    """Request for extraction endpoint."""

    use_llm_enhancement: bool = Field(
        default=True,
        description="Whether to use LLM for low-confidence extractions"
    )
    llm_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for triggering LLM enhancement"
    )


class ExtractResponse(BaseModel):
    """Response from extraction endpoint."""

    job_id: str
    status: str
    extractions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extraction results per file"
    )
    overall_confidence: float = Field(default=0.0)
    message: str = Field(default="Extraction completed")


class MappingSuggestion(BaseModel):
    """A single field mapping suggestion."""

    source_field: str
    target_field: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_value: Optional[Any] = None
    reasoning: Optional[str] = None


class MappingSuggestionsResponse(BaseModel):
    """Response with mapping suggestions for an entity."""

    job_id: str
    entity_type: str
    suggestions: List[MappingSuggestion] = Field(default_factory=list)
    unmapped_fields: List[str] = Field(default_factory=list)


class ApplyMappingRequest(BaseModel):
    """Request to apply field mappings."""

    entity: str = Field(..., description="Entity type: epic, estimation, tdd, story")
    mappings: Dict[str, str] = Field(
        ...,
        description="Field mappings: source_field -> target_field"
    )
    user_overrides: Dict[str, Any] = Field(
        default_factory=dict,
        description="Manual value overrides for specific fields"
    )


class TransformResponse(BaseModel):
    """Response from transformation endpoint."""

    job_id: str
    status: str
    records_created: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of records created per entity type"
    )
    relationship_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of entity relationships"
    )
    validation_warnings: List[str] = Field(default_factory=list)
    message: str = Field(default="Transformation completed")


class PreviewRequest(BaseModel):
    """Request for data preview."""

    entity: str = Field(..., description="Entity type to preview")
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class PreviewResponse(BaseModel):
    """Response with data preview."""

    job_id: str
    entity: str
    data: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = Field(default=0)
    validation_results: Dict[str, Any] = Field(default_factory=dict)


class ValidationResponse(BaseModel):
    """Response from validation endpoint."""

    job_id: str
    valid: bool
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    relationship_integrity: Dict[str, Any] = Field(default_factory=dict)


class ExportRequest(BaseModel):
    """Request for data export."""

    entities: List[str] = Field(
        default_factory=lambda: ["epics", "estimations", "tdds", "stories"],
        description="List of entities to export"
    )
    sync_vector_db: bool = Field(
        default=True,
        description="Whether to trigger vector DB reindex"
    )
    backup_existing: bool = Field(
        default=True,
        description="Whether to backup existing CSV files"
    )


class ExportResponse(BaseModel):
    """Response from export endpoint."""

    job_id: str
    status: str
    files_created: List[str] = Field(default_factory=list)
    records_per_file: Dict[str, int] = Field(default_factory=dict)
    vector_db_synced: bool = Field(default=False)
    download_paths: Dict[str, str] = Field(default_factory=dict)
    message: str = Field(default="Export completed")


class BatchStatusResponse(BaseModel):
    """Response for batch watcher status."""

    running: bool
    watching_path: Optional[str] = None
    jobs_processed_today: int = Field(default=0)


class JobListResponse(BaseModel):
    """Response with list of jobs."""

    jobs: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = Field(default=0)
    page: int = Field(default=1)
    page_size: int = Field(default=50)


class HealthResponse(BaseModel):
    """Response from health endpoint."""

    status: str = Field(default="healthy")
    version: str
    ollama_status: str
    disk_space_mb: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
