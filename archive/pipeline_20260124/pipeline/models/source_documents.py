"""
Source document models for file uploads.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Types of source documents the pipeline accepts."""

    EPIC = "epic"
    ESTIMATION = "estimation"
    TDD = "tdd"
    STORY = "story"
    UNKNOWN = "unknown"


class SourceDocument(BaseModel):
    """Model for a source document before processing."""

    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Path where file is stored")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    file_type: str = Field(..., description="File extension (.docx, .xlsx)")
    document_type: DocumentType = Field(
        default=DocumentType.UNKNOWN,
        description="Detected document type (epic, estimation, tdd, story)"
    )
    uploaded_at: datetime = Field(
        default_factory=datetime.utcnow, description="Upload timestamp"
    )


class UploadedFile(BaseModel):
    """Information about an uploaded file."""

    filename: str
    size: int
    content_type: Optional[str] = None
    document_type: DocumentType = DocumentType.UNKNOWN


def detect_document_type(filename: str) -> DocumentType:
    """
    Detect document type from filename patterns.

    Args:
        filename: Original filename

    Returns:
        Detected DocumentType
    """
    filename_lower = filename.lower()

    # Epic patterns
    if any(p in filename_lower for p in ["epic", "requirement", "req"]):
        return DocumentType.EPIC

    # Estimation patterns (usually Excel)
    if any(p in filename_lower for p in ["estimation", "estimate", "est"]):
        return DocumentType.ESTIMATION
    if filename_lower.endswith((".xlsx", ".xls")):
        return DocumentType.ESTIMATION

    # TDD patterns
    if any(p in filename_lower for p in ["tdd", "technical_design", "design"]):
        return DocumentType.TDD

    # Story patterns
    if any(p in filename_lower for p in ["story", "stories", "task"]):
        return DocumentType.STORY

    return DocumentType.UNKNOWN
