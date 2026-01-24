"""
Base transformer classes.

Defines the abstract interface for transforming extracted data
into target schema entities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel

from pipeline.core.id_generator import IDGenerator
from pipeline.core.relationship_manager import RelationshipManager
from pipeline.extractors.base import ExtractedData


TTarget = TypeVar("TTarget", bound=BaseModel)


@dataclass
class TransformationError:
    """Represents an error during transformation."""

    field_name: str
    message: str
    severity: str = "error"  # "error" or "warning"
    source_value: Any = None


@dataclass
class TransformationResult(Generic[TTarget]):
    """Result of a transformation operation."""

    success: bool
    entity: Optional[TTarget] = None
    errors: List[TransformationError] = None
    warnings: List[TransformationError] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "entity": self.entity.model_dump() if self.entity else None,
            "errors": [
                {"field": e.field_name, "message": e.message} for e in self.errors
            ],
            "warnings": [
                {"field": w.field_name, "message": w.message} for w in self.warnings
            ],
        }


class BaseTransformer(ABC, Generic[TTarget]):
    """
    Abstract base class for entity transformers.

    Transformers convert raw extracted data into validated
    target schema entities, generating IDs and establishing
    relationships.
    """

    @abstractmethod
    async def transform(
        self,
        extracted: ExtractedData,
        mapping: Dict[str, str],
        id_gen: IDGenerator,
        rel_mgr: RelationshipManager,
        position: int = 0,
    ) -> TransformationResult[TTarget]:
        """
        Transform extracted data to target schema.

        Args:
            extracted: Raw extracted data from document
            mapping: Field mapping from source to target fields
            id_gen: ID generator for creating primary keys
            rel_mgr: Relationship manager for FK tracking
            position: Position index for position-based linking

        Returns:
            TransformationResult with entity or errors
        """
        pass

    @abstractmethod
    def get_target_schema(self) -> Type[TTarget]:
        """
        Get the Pydantic model class for the target schema.

        Returns:
            Type of the target Pydantic model
        """
        pass

    def validate(self, entity: TTarget) -> List[TransformationError]:
        """
        Validate a transformed entity.

        Override in subclasses for entity-specific validation.

        Args:
            entity: Entity to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Basic Pydantic validation happens during model creation
        # Additional validation can be added here

        return errors

    def _get_mapped_value(
        self,
        extracted: ExtractedData,
        mapping: Dict[str, str],
        target_field: str,
        default: Any = None,
    ) -> Any:
        """
        Get value for a target field using the mapping.

        Args:
            extracted: Extracted data
            mapping: Field mapping
            target_field: Target field name
            default: Default value if not found

        Returns:
            Mapped value or default
        """
        # Find source field for this target
        source_field = None
        for src, tgt in mapping.items():
            if tgt == target_field:
                source_field = src
                break

        if not source_field:
            return default

        # Try to get value from extracted data
        value = extracted.get_field_value(source_field)
        if value is not None:
            return value

        # Try key-value pairs
        if source_field in extracted.key_value_pairs:
            return extracted.key_value_pairs[source_field]

        return default

    def _get_table_rows(
        self, extracted: ExtractedData, table_index: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get rows from an extracted table.

        Args:
            extracted: Extracted data
            table_index: Index of table to use

        Returns:
            List of row dictionaries
        """
        return extracted.get_table_as_dicts(table_index)
