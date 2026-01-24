"""
Base extractor classes and data models.

Defines the abstract interface for all document extractors and the
common data structures for extracted content.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ExtractedField:
    """A single extracted field with value and metadata."""

    name: str
    value: Any
    confidence: float = 1.0
    source_location: Optional[str] = None  # Where in document this was found
    data_type: str = "string"  # string, number, date, email, array, etc.


@dataclass
class ExtractedTable:
    """A table extracted from a document."""

    headers: List[str]
    rows: List[Dict[str, Any]]
    source_location: Optional[str] = None
    confidence: float = 1.0


@dataclass
class ExtractedList:
    """A list (bulleted/numbered) extracted from a document."""

    items: List[str]
    list_type: str = "bullet"  # bullet, numbered
    heading: Optional[str] = None  # Heading before the list
    source_location: Optional[str] = None


@dataclass
class DocumentMetadata:
    """Metadata about the source document."""

    filename: str
    file_path: str
    file_size: int
    file_type: str  # docx, xlsx, etc.
    title: Optional[str] = None
    author: Optional[str] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    page_count: Optional[int] = None
    sheet_names: Optional[List[str]] = None  # For Excel files


@dataclass
class ExtractedData:
    """
    Complete extraction result from a document.

    Contains all structured data extracted from a source document,
    including text content, tables, lists, and metadata.
    """

    # Raw content
    raw_content: str = ""  # Full text content
    raw_sections: Dict[str, str] = field(default_factory=dict)  # Section name -> content

    # Structured extractions
    fields: Dict[str, ExtractedField] = field(default_factory=dict)
    tables: List[ExtractedTable] = field(default_factory=list)
    lists: List[ExtractedList] = field(default_factory=list)

    # Key-value pairs detected (e.g., "Priority: High")
    key_value_pairs: Dict[str, str] = field(default_factory=dict)

    # Pattern matches
    jira_ids: List[str] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)

    # Confidence scores per field
    confidence_scores: Dict[str, float] = field(default_factory=dict)

    # Document metadata
    metadata: Optional[DocumentMetadata] = None

    # Overall extraction confidence
    overall_confidence: float = 1.0

    # Extraction warnings/notes
    warnings: List[str] = field(default_factory=list)

    def get_field_value(
        self, field_name: str, default: Any = None
    ) -> Any:
        """
        Get a field value by name, with optional default.

        Args:
            field_name: Name of the field to retrieve
            default: Default value if field not found

        Returns:
            Field value or default
        """
        if field_name in self.fields:
            return self.fields[field_name].value
        if field_name in self.key_value_pairs:
            return self.key_value_pairs[field_name]
        return default

    def get_first_table(self) -> Optional[ExtractedTable]:
        """Get the first extracted table, if any."""
        return self.tables[0] if self.tables else None

    def get_table_as_dicts(self, table_index: int = 0) -> List[Dict[str, Any]]:
        """
        Get a table's rows as list of dictionaries.

        Args:
            table_index: Index of table to retrieve

        Returns:
            List of row dictionaries
        """
        if table_index < len(self.tables):
            return self.tables[table_index].rows
        return []

    def to_dict(self) -> Dict[str, Any]:
        """Convert extraction to dictionary for serialization."""
        return {
            "raw_content": self.raw_content[:1000] + "..." if len(self.raw_content) > 1000 else self.raw_content,
            "sections": list(self.raw_sections.keys()),
            "fields": {
                name: {"value": f.value, "confidence": f.confidence}
                for name, f in self.fields.items()
            },
            "tables_count": len(self.tables),
            "lists_count": len(self.lists),
            "key_value_pairs": self.key_value_pairs,
            "jira_ids": self.jira_ids,
            "emails": self.emails,
            "dates": self.dates,
            "overall_confidence": self.overall_confidence,
            "warnings": self.warnings,
            "metadata": {
                "filename": self.metadata.filename if self.metadata else None,
                "file_type": self.metadata.file_type if self.metadata else None,
            },
        }


class BaseExtractor(ABC):
    """
    Abstract base class for document extractors.

    All document extractors must implement the extract method and
    specify their supported file extensions.
    """

    @abstractmethod
    async def extract(self, file_path: Path) -> ExtractedData:
        """
        Extract structured data from a document.

        Args:
            file_path: Path to the document file

        Returns:
            ExtractedData containing all extracted content

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If file type is not supported
        """
        pass

    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        Get list of file extensions this extractor supports.

        Returns:
            List of extensions (e.g., [".docx", ".doc"])
        """
        pass

    def supports_file(self, file_path: Path) -> bool:
        """
        Check if this extractor supports the given file.

        Args:
            file_path: Path to check

        Returns:
            True if file extension is supported
        """
        return file_path.suffix.lower() in self.get_supported_extensions()

    def _validate_file(self, file_path: Path) -> None:
        """
        Validate file exists and is supported.

        Args:
            file_path: Path to validate

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If file type is not supported
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not self.supports_file(file_path):
            raise ValueError(
                f"Unsupported file type: {file_path.suffix}. "
                f"Supported: {self.get_supported_extensions()}"
            )
