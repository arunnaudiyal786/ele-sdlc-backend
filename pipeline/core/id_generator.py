"""
ID Generator for pipeline entities.

Generates unique primary keys with consistent formats:
- Epics: EPIC-001, EPIC-002, etc.
- Estimations: EST-001, EST-002, etc.
- TDDs: TDD-001, TDD-002, etc.
- Stories: Uses existing Jira ID or generates STORY-001
- Modules: MOD-PAY-001, MOD-AUTH-001, etc.
"""

import re
from typing import Dict, Optional, Set

from pipeline.core.config import get_pipeline_settings


class IDGenerator:
    """
    Generates unique primary keys for pipeline entities.

    Thread-safe for single job processing. Each job should create its own
    IDGenerator instance to maintain separate counter state.
    """

    def __init__(self, job_id: str):
        """
        Initialize ID generator for a specific job.

        Args:
            job_id: The job ID this generator belongs to
        """
        self.job_id = job_id
        self.settings = get_pipeline_settings()

        # Counters for each entity type
        self.counters: Dict[str, int] = {
            "epic": 0,
            "estimation": 0,
            "tdd": 0,
            "story": 0,
            "module": 0,
        }

        # Track all generated IDs to ensure uniqueness
        self.used_ids: Set[str] = set()

        # Track module counters per domain
        self.module_domain_counters: Dict[str, int] = {}

    def generate_epic_id(self, prefix: Optional[str] = None) -> str:
        """
        Generate a new epic ID.

        Args:
            prefix: Optional prefix override (default: EPIC)

        Returns:
            New epic ID in format EPIC-NNN
        """
        prefix = prefix or self.settings.epic_id_prefix
        self.counters["epic"] += 1
        id_value = f"{prefix}-{self.counters['epic']:0{self.settings.id_padding}d}"
        self.used_ids.add(id_value)
        return id_value

    def generate_estimation_id(self, prefix: Optional[str] = None) -> str:
        """
        Generate a new estimation ID.

        Args:
            prefix: Optional prefix override (default: EST)

        Returns:
            New estimation ID in format EST-NNN
        """
        prefix = prefix or self.settings.estimation_id_prefix
        self.counters["estimation"] += 1
        id_value = f"{prefix}-{self.counters['estimation']:0{self.settings.id_padding}d}"
        self.used_ids.add(id_value)
        return id_value

    def generate_tdd_id(self, prefix: Optional[str] = None) -> str:
        """
        Generate a new TDD ID.

        Args:
            prefix: Optional prefix override (default: TDD)

        Returns:
            New TDD ID in format TDD-NNN
        """
        prefix = prefix or self.settings.tdd_id_prefix
        self.counters["tdd"] += 1
        id_value = f"{prefix}-{self.counters['tdd']:0{self.settings.id_padding}d}"
        self.used_ids.add(id_value)
        return id_value

    def generate_story_id(self, jira_id: Optional[str] = None) -> str:
        """
        Generate a story ID, preferring existing Jira ID if valid.

        Args:
            jira_id: Optional existing Jira ID to use

        Returns:
            Jira ID if valid, otherwise generated STORY-NNN
        """
        # Use existing Jira ID if valid format
        if jira_id and self.is_valid_jira_id(jira_id):
            # Check for duplicates
            if jira_id not in self.used_ids:
                self.used_ids.add(jira_id)
                return jira_id

        # Generate new story ID
        prefix = self.settings.story_id_prefix
        self.counters["story"] += 1
        id_value = f"{prefix}-{self.counters['story']:0{self.settings.id_padding}d}"
        self.used_ids.add(id_value)
        return id_value

    def generate_module_id(self, domain: str) -> str:
        """
        Generate a module ID for a specific domain.

        Args:
            domain: Domain name (e.g., "Payment", "Auth", "Order")

        Returns:
            Module ID in format MOD-{DOMAIN}-NNN
        """
        # Normalize domain to uppercase, max 3-4 chars
        domain_code = domain.upper()[:4].replace(" ", "").replace("-", "")
        if len(domain_code) < 2:
            domain_code = "GEN"  # Generic fallback

        # Initialize domain counter if needed
        if domain_code not in self.module_domain_counters:
            self.module_domain_counters[domain_code] = 0

        self.module_domain_counters[domain_code] += 1
        self.counters["module"] += 1

        id_value = (
            f"{self.settings.module_id_prefix}-{domain_code}-"
            f"{self.module_domain_counters[domain_code]:0{self.settings.id_padding}d}"
        )
        self.used_ids.add(id_value)
        return id_value

    @staticmethod
    def is_valid_jira_id(jira_id: str) -> bool:
        """
        Check if a string is a valid Jira ID format.

        Valid formats:
        - MMO-12323 (standard Jira project-number)
        - MM16783 (alternate MM format)
        - PROJ-123 (any uppercase project code with numbers)

        Args:
            jira_id: String to validate

        Returns:
            True if valid Jira ID format
        """
        if not jira_id:
            return False

        # Standard Jira format: PROJECT-NUMBER
        if re.match(r"^[A-Z]+-\d+$", jira_id):
            return True

        # MM format: MM followed by digits
        if re.match(r"^MM\d+$", jira_id):
            return True

        return False

    def register_existing_id(self, id_value: str) -> None:
        """
        Register an existing ID to prevent duplicates.

        Use this when loading existing data that should not be regenerated.

        Args:
            id_value: Existing ID to register
        """
        self.used_ids.add(id_value)

    def is_id_used(self, id_value: str) -> bool:
        """
        Check if an ID has already been generated or registered.

        Args:
            id_value: ID to check

        Returns:
            True if ID is already in use
        """
        return id_value in self.used_ids

    def get_counters(self) -> Dict[str, int]:
        """
        Get current counter values for all entity types.

        Returns:
            Dictionary of entity type to current count
        """
        return self.counters.copy()

    def get_stats(self) -> Dict[str, any]:
        """
        Get generation statistics.

        Returns:
            Dictionary with generation stats
        """
        return {
            "job_id": self.job_id,
            "counters": self.counters.copy(),
            "total_ids_generated": len(self.used_ids),
            "module_domains": list(self.module_domain_counters.keys()),
        }
