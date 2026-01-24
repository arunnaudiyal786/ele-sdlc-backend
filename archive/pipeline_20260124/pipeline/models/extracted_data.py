"""
Models for extracted document data.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExtractedField(BaseModel):
    """A single extracted field with value and metadata."""

    name: str = Field(..., description="Field name")
    value: Any = Field(..., description="Extracted value")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    source_location: Optional[str] = Field(None, description="Where in document found")
    data_type: str = Field(default="string", description="Detected data type")


class ExtractedTable(BaseModel):
    """A table extracted from a document."""

    headers: List[str] = Field(default_factory=list, description="Column headers")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="Data rows as dicts")
    source_location: Optional[str] = Field(None, description="Table location in document")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class DocumentExtraction(BaseModel):
    """Complete extraction result from a document."""

    filename: str = Field(..., description="Source filename")
    document_type: str = Field(..., description="Type of document extracted")
    raw_content: str = Field(default="", description="Full text content")
    fields: Dict[str, ExtractedField] = Field(default_factory=dict, description="Extracted fields")
    tables: List[ExtractedTable] = Field(default_factory=list, description="Extracted tables")
    key_value_pairs: Dict[str, str] = Field(default_factory=dict, description="Detected key-value pairs")
    jira_ids: List[str] = Field(default_factory=list, description="Detected Jira IDs")
    emails: List[str] = Field(default_factory=list, description="Detected email addresses")
    dates: List[str] = Field(default_factory=list, description="Detected dates")
    overall_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
