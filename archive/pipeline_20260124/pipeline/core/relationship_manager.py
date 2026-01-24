"""
Relationship Manager for tracking entity relationships.

Manages foreign key relationships between pipeline entities:
- Epic → Estimation (1:N)
- Epic → TDD (1:N)
- Estimation → TDD (1:1)
- Story → Epic, Estimation, TDD (N:1 each)

Uses position-based linking as the default strategy for matching
entities across documents when explicit IDs are not present.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ValidationError:
    """Represents a relationship validation error."""

    entity_type: str
    entity_id: str
    field_name: str
    message: str
    severity: str = "error"  # "error" or "warning"


@dataclass
class EntityRelationships:
    """Tracks relationships for a single entity."""

    entity_id: str
    entity_type: str
    parent_ids: Dict[str, str] = field(default_factory=dict)  # field_name -> parent_id
    child_ids: Dict[str, List[str]] = field(default_factory=dict)  # field_name -> [child_ids]


class RelationshipManager:
    """
    Manages entity relationships within a pipeline job.

    Tracks parent-child relationships between entities and validates
    foreign key integrity before export.
    """

    def __init__(self, job_id: str):
        """
        Initialize relationship manager for a specific job.

        Args:
            job_id: The job ID this manager belongs to
        """
        self.job_id = job_id

        # Primary entity registries: id -> source identifier
        self.epics: Dict[str, str] = {}  # epic_id -> source_identifier
        self.estimations: Dict[str, str] = {}  # dev_est_id -> source_identifier
        self.tdds: Dict[str, str] = {}  # tdd_id -> source_identifier
        self.stories: Dict[str, str] = {}  # jira_story_id -> source_identifier

        # Reverse lookup maps: source_identifier -> id
        self.epic_by_source: Dict[str, str] = {}
        self.estimation_by_source: Dict[str, str] = {}
        self.tdd_by_source: Dict[str, str] = {}

        # Relationship maps
        self.estimation_to_epic: Dict[str, str] = {}  # dev_est_id -> epic_id
        self.tdd_to_epic: Dict[str, str] = {}  # tdd_id -> epic_id
        self.tdd_to_estimation: Dict[str, str] = {}  # tdd_id -> dev_est_id
        self.story_to_epic: Dict[str, str] = {}  # jira_story_id -> epic_id
        self.story_to_estimation: Dict[str, str] = {}  # jira_story_id -> dev_est_id
        self.story_to_tdd: Dict[str, str] = {}  # jira_story_id -> tdd_id

        # Reverse relationship maps (parent to children)
        self.epic_estimations: Dict[str, List[str]] = {}  # epic_id -> [dev_est_ids]
        self.epic_tdds: Dict[str, List[str]] = {}  # epic_id -> [tdd_ids]
        self.epic_stories: Dict[str, List[str]] = {}  # epic_id -> [story_ids]

        # Position-based linking arrays (for fallback matching)
        self.epic_order: List[str] = []
        self.estimation_order: List[str] = []
        self.tdd_order: List[str] = []

    def register_epic(
        self, epic_id: str, source_identifier: Optional[str] = None
    ) -> None:
        """
        Register a new epic entity.

        Args:
            epic_id: The epic's primary key
            source_identifier: Optional identifier from source document (jira_id, name)
        """
        source_id = source_identifier or epic_id
        self.epics[epic_id] = source_id
        self.epic_by_source[source_id] = epic_id
        self.epic_order.append(epic_id)

        # Initialize child lists
        if epic_id not in self.epic_estimations:
            self.epic_estimations[epic_id] = []
        if epic_id not in self.epic_tdds:
            self.epic_tdds[epic_id] = []
        if epic_id not in self.epic_stories:
            self.epic_stories[epic_id] = []

    def register_estimation(
        self,
        dev_est_id: str,
        epic_id: str,
        source_identifier: Optional[str] = None,
    ) -> None:
        """
        Register a new estimation entity and link to epic.

        Args:
            dev_est_id: The estimation's primary key
            epic_id: Foreign key to parent epic
            source_identifier: Optional identifier from source document
        """
        source_id = source_identifier or dev_est_id
        self.estimations[dev_est_id] = source_id
        self.estimation_by_source[source_id] = dev_est_id
        self.estimation_order.append(dev_est_id)

        # Link to epic
        self.estimation_to_epic[dev_est_id] = epic_id
        if epic_id in self.epic_estimations:
            self.epic_estimations[epic_id].append(dev_est_id)

    def register_tdd(
        self,
        tdd_id: str,
        epic_id: str,
        dev_est_id: str,
        source_identifier: Optional[str] = None,
    ) -> None:
        """
        Register a new TDD entity and link to epic and estimation.

        Args:
            tdd_id: The TDD's primary key
            epic_id: Foreign key to parent epic
            dev_est_id: Foreign key to estimation
            source_identifier: Optional identifier from source document
        """
        source_id = source_identifier or tdd_id
        self.tdds[tdd_id] = source_id
        self.tdd_by_source[source_id] = tdd_id
        self.tdd_order.append(tdd_id)

        # Link to epic and estimation
        self.tdd_to_epic[tdd_id] = epic_id
        self.tdd_to_estimation[tdd_id] = dev_est_id
        if epic_id in self.epic_tdds:
            self.epic_tdds[epic_id].append(tdd_id)

    def register_story(
        self,
        jira_story_id: str,
        epic_id: str,
        dev_est_id: str,
        tdd_id: str,
        source_identifier: Optional[str] = None,
    ) -> None:
        """
        Register a new story entity and link to all parents.

        Args:
            jira_story_id: The story's primary key
            epic_id: Foreign key to epic
            dev_est_id: Foreign key to estimation
            tdd_id: Foreign key to TDD
            source_identifier: Optional identifier from source document
        """
        source_id = source_identifier or jira_story_id
        self.stories[jira_story_id] = source_id

        # Link to all parents
        self.story_to_epic[jira_story_id] = epic_id
        self.story_to_estimation[jira_story_id] = dev_est_id
        self.story_to_tdd[jira_story_id] = tdd_id
        if epic_id in self.epic_stories:
            self.epic_stories[epic_id].append(jira_story_id)

    def resolve_epic_id(self, source_data: Dict[str, Any]) -> Optional[str]:
        """
        Try to find an existing epic by various source identifiers.

        Checks (in order):
        1. jira_id field
        2. epic_name field
        3. req_id field

        Args:
            source_data: Dictionary with potential identifier fields

        Returns:
            Epic ID if found, None otherwise
        """
        # Try jira_id first
        jira_id = source_data.get("jira_id")
        if jira_id and jira_id in self.epic_by_source:
            return self.epic_by_source[jira_id]

        # Try epic_name
        epic_name = source_data.get("epic_name")
        if epic_name and epic_name in self.epic_by_source:
            return self.epic_by_source[epic_name]

        # Try req_id
        req_id = source_data.get("req_id")
        if req_id and req_id in self.epic_by_source:
            return self.epic_by_source[req_id]

        return None

    def get_epic_by_position(self, position: int) -> Optional[str]:
        """
        Get epic ID by position in registration order.

        Args:
            position: Zero-based position index

        Returns:
            Epic ID at position, or None if out of range
        """
        if 0 <= position < len(self.epic_order):
            return self.epic_order[position]
        return None

    def get_estimation_for_epic(self, epic_id: str) -> Optional[str]:
        """
        Get the first estimation linked to an epic.

        Args:
            epic_id: Epic to find estimation for

        Returns:
            First dev_est_id linked to epic, or None
        """
        estimations = self.epic_estimations.get(epic_id, [])
        return estimations[0] if estimations else None

    def get_tdd_for_epic(self, epic_id: str) -> Optional[str]:
        """
        Get the first TDD linked to an epic.

        Args:
            epic_id: Epic to find TDD for

        Returns:
            First tdd_id linked to epic, or None
        """
        tdds = self.epic_tdds.get(epic_id, [])
        return tdds[0] if tdds else None

    def get_estimation_by_position(self, position: int) -> Optional[str]:
        """
        Get estimation ID by position in registration order.

        Args:
            position: Zero-based position index

        Returns:
            Estimation ID at position, or None if out of range
        """
        if 0 <= position < len(self.estimation_order):
            return self.estimation_order[position]
        return None

    def get_tdd_by_position(self, position: int) -> Optional[str]:
        """
        Get TDD ID by position in registration order.

        Args:
            position: Zero-based position index

        Returns:
            TDD ID at position, or None if out of range
        """
        if 0 <= position < len(self.tdd_order):
            return self.tdd_order[position]
        return None

    def validate_all_relationships(self) -> List[ValidationError]:
        """
        Validate all foreign key relationships.

        Checks that all FK references point to existing entities.

        Returns:
            List of validation errors found
        """
        errors: List[ValidationError] = []

        # Validate estimation -> epic relationships
        for dev_est_id, epic_id in self.estimation_to_epic.items():
            if epic_id not in self.epics:
                errors.append(
                    ValidationError(
                        entity_type="estimation",
                        entity_id=dev_est_id,
                        field_name="epic_id",
                        message=f"Referenced epic '{epic_id}' does not exist",
                    )
                )

        # Validate TDD -> epic relationships
        for tdd_id, epic_id in self.tdd_to_epic.items():
            if epic_id not in self.epics:
                errors.append(
                    ValidationError(
                        entity_type="tdd",
                        entity_id=tdd_id,
                        field_name="epic_id",
                        message=f"Referenced epic '{epic_id}' does not exist",
                    )
                )

        # Validate TDD -> estimation relationships
        for tdd_id, dev_est_id in self.tdd_to_estimation.items():
            if dev_est_id not in self.estimations:
                errors.append(
                    ValidationError(
                        entity_type="tdd",
                        entity_id=tdd_id,
                        field_name="dev_est_id",
                        message=f"Referenced estimation '{dev_est_id}' does not exist",
                    )
                )

        # Validate story relationships
        for story_id, epic_id in self.story_to_epic.items():
            if epic_id not in self.epics:
                errors.append(
                    ValidationError(
                        entity_type="story",
                        entity_id=story_id,
                        field_name="epic_id",
                        message=f"Referenced epic '{epic_id}' does not exist",
                    )
                )

        for story_id, dev_est_id in self.story_to_estimation.items():
            if dev_est_id not in self.estimations:
                errors.append(
                    ValidationError(
                        entity_type="story",
                        entity_id=story_id,
                        field_name="dev_est_id",
                        message=f"Referenced estimation '{dev_est_id}' does not exist",
                    )
                )

        for story_id, tdd_id in self.story_to_tdd.items():
            if tdd_id not in self.tdds:
                errors.append(
                    ValidationError(
                        entity_type="story",
                        entity_id=story_id,
                        field_name="tdd_id",
                        message=f"Referenced TDD '{tdd_id}' does not exist",
                    )
                )

        return errors

    def get_full_lineage(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """
        Get full parent/child chain for an entity.

        Args:
            entity_type: Type of entity (epic, estimation, tdd, story)
            entity_id: Entity ID to get lineage for

        Returns:
            Dictionary with parents and children
        """
        lineage: Dict[str, Any] = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "parents": {},
            "children": {},
        }

        if entity_type == "epic":
            lineage["children"]["estimations"] = self.epic_estimations.get(entity_id, [])
            lineage["children"]["tdds"] = self.epic_tdds.get(entity_id, [])
            lineage["children"]["stories"] = self.epic_stories.get(entity_id, [])

        elif entity_type == "estimation":
            lineage["parents"]["epic_id"] = self.estimation_to_epic.get(entity_id)

        elif entity_type == "tdd":
            lineage["parents"]["epic_id"] = self.tdd_to_epic.get(entity_id)
            lineage["parents"]["dev_est_id"] = self.tdd_to_estimation.get(entity_id)

        elif entity_type == "story":
            lineage["parents"]["epic_id"] = self.story_to_epic.get(entity_id)
            lineage["parents"]["dev_est_id"] = self.story_to_estimation.get(entity_id)
            lineage["parents"]["tdd_id"] = self.story_to_tdd.get(entity_id)

        return lineage

    def export_relationship_graph(self) -> Dict[str, Any]:
        """
        Export complete relationship map for visualization.

        Returns:
            Dictionary with all entities and relationships
        """
        return {
            "job_id": self.job_id,
            "entities": {
                "epics": list(self.epics.keys()),
                "estimations": list(self.estimations.keys()),
                "tdds": list(self.tdds.keys()),
                "stories": list(self.stories.keys()),
            },
            "relationships": {
                "estimation_to_epic": self.estimation_to_epic.copy(),
                "tdd_to_epic": self.tdd_to_epic.copy(),
                "tdd_to_estimation": self.tdd_to_estimation.copy(),
                "story_to_epic": self.story_to_epic.copy(),
                "story_to_estimation": self.story_to_estimation.copy(),
                "story_to_tdd": self.story_to_tdd.copy(),
            },
            "counts": {
                "epics": len(self.epics),
                "estimations": len(self.estimations),
                "tdds": len(self.tdds),
                "stories": len(self.stories),
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get relationship statistics.

        Returns:
            Dictionary with relationship stats
        """
        return {
            "job_id": self.job_id,
            "entity_counts": {
                "epics": len(self.epics),
                "estimations": len(self.estimations),
                "tdds": len(self.tdds),
                "stories": len(self.stories),
            },
            "relationship_counts": {
                "estimation_epic_links": len(self.estimation_to_epic),
                "tdd_epic_links": len(self.tdd_to_epic),
                "tdd_estimation_links": len(self.tdd_to_estimation),
                "story_links": len(self.story_to_epic),
            },
        }
