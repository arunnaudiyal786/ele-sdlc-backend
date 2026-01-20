"""
TDD (Technical Design Document) entity transformer.

Transforms extracted document data to TDD schema.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type

from pipeline.core.id_generator import IDGenerator
from pipeline.core.relationship_manager import RelationshipManager
from pipeline.extractors.base import ExtractedData
from pipeline.transformers.base import BaseTransformer, TransformationError, TransformationResult
from pipeline.transformers.normalizers import (
    array_to_json_string,
    clean_text,
    email_normalizer,
    enum_normalizer,
)
from shared.schemas.tdd import TDD


class TDDTransformer(BaseTransformer[TDD]):
    """
    Transforms extracted data to TDD entities.

    Handles:
    - Document structure parsing
    - Technical component extraction
    - Relationship linking to epics and estimations
    """

    def get_target_schema(self) -> Type[TDD]:
        return TDD

    async def transform(
        self,
        extracted: ExtractedData,
        mapping: Dict[str, str],
        id_gen: IDGenerator,
        rel_mgr: RelationshipManager,
        position: int = 0,
    ) -> TransformationResult[TDD]:
        """
        Transform extracted data to TDD entity.

        Args:
            extracted: Extracted document data
            mapping: Field mapping
            id_gen: ID generator
            rel_mgr: Relationship manager
            position: Position index for linking

        Returns:
            TransformationResult with TDD entity
        """
        errors = []
        warnings = []

        try:
            # Generate TDD ID
            tdd_id = id_gen.generate_tdd_id()

            # Resolve epic_id by position
            epic_id = rel_mgr.get_epic_by_position(position)
            if not epic_id:
                epic_id = rel_mgr.get_epic_by_position(0)
            if not epic_id:
                # Generate placeholder
                epic_id = id_gen.generate_epic_id()
                rel_mgr.register_epic(epic_id, f"auto_epic_tdd_{position}")
                warnings.append(
                    TransformationError(
                        field_name="epic_id",
                        message="No epic found, generated placeholder",
                        severity="warning",
                    )
                )

            # Resolve dev_est_id
            dev_est_id = rel_mgr.get_estimation_for_epic(epic_id)
            if not dev_est_id:
                dev_est_id = rel_mgr.get_estimation_by_position(position)
            if not dev_est_id:
                # Generate placeholder
                dev_est_id = id_gen.generate_estimation_id()
                rel_mgr.register_estimation(dev_est_id, epic_id, f"auto_est_tdd_{position}")
                warnings.append(
                    TransformationError(
                        field_name="dev_est_id",
                        message="No estimation found, generated placeholder",
                        severity="warning",
                    )
                )

            # TDD name - from document title or first heading
            tdd_name = self._get_mapped_value(extracted, mapping, "tdd_name")
            if not tdd_name and extracted.metadata and extracted.metadata.title:
                tdd_name = extracted.metadata.title
            if not tdd_name and extracted.raw_sections:
                # Use first section heading
                tdd_name = list(extracted.raw_sections.keys())[0]
            tdd_name = clean_text(tdd_name) or f"TDD {position + 1}"

            # Description - from overview section or full content
            tdd_description = self._get_mapped_value(extracted, mapping, "tdd_description")
            if not tdd_description:
                # Try to find overview/summary section
                for section_name, content in extracted.raw_sections.items():
                    section_lower = section_name.lower()
                    if any(kw in section_lower for kw in ["overview", "summary", "introduction", "description"]):
                        tdd_description = content
                        break
            if not tdd_description:
                tdd_description = extracted.raw_content[:1000] if extracted.raw_content else "No description"
            tdd_description = clean_text(tdd_description)

            # Version
            version = self._get_mapped_value(extracted, mapping, "tdd_version")
            if not version:
                # Try to find version in content
                import re
                version_match = re.search(r"version[:\s]*([0-9]+\.?[0-9]*)", extracted.raw_content, re.IGNORECASE)
                if version_match:
                    version = version_match.group(1)
            version = version or "1.0"
            if re.match(r"^\d+$", version):
                version = f"{version}.0"

            # Status
            status = self._get_mapped_value(extracted, mapping, "tdd_status")
            status = enum_normalizer(
                status,
                ["Draft", "In Review", "Approved"],
                default="Draft"
            )

            # Author
            author = self._get_mapped_value(extracted, mapping, "tdd_author")
            if not author and extracted.metadata and extracted.metadata.author:
                author = extracted.metadata.author
            if not author and extracted.emails:
                author = extracted.emails[0]
            author = email_normalizer(author) or "unknown@company.com"

            # Technical components - extract from content or lists
            tech_components = self._extract_technical_components(extracted, mapping)

            # Design decisions
            design_decisions = self._get_mapped_value(extracted, mapping, "design_decisions")
            if not design_decisions:
                for section_name, content in extracted.raw_sections.items():
                    if "decision" in section_name.lower() or "design" in section_name.lower():
                        design_decisions = content
                        break
            design_decisions = clean_text(design_decisions) or ""

            # Dependencies
            dependencies = self._extract_dependencies(extracted, mapping)

            # Architecture pattern
            arch_pattern = self._get_mapped_value(extracted, mapping, "architecture_pattern")
            if not arch_pattern:
                arch_pattern = self._detect_architecture_pattern(extracted.raw_content)
            arch_pattern = clean_text(arch_pattern) or ""

            # Security considerations
            security = self._get_mapped_value(extracted, mapping, "security_considerations")
            if not security:
                for section_name, content in extracted.raw_sections.items():
                    if "security" in section_name.lower():
                        security = content
                        break
            security = clean_text(security) or ""

            # Performance requirements
            performance = self._get_mapped_value(extracted, mapping, "performance_requirements")
            if not performance:
                for section_name, content in extracted.raw_sections.items():
                    if "performance" in section_name.lower() or "sla" in section_name.lower():
                        performance = content
                        break
            performance = clean_text(performance) or ""

            # Create TDD entity
            tdd = TDD(
                tdd_id=tdd_id,
                epic_id=epic_id,
                dev_est_id=dev_est_id,
                tdd_name=tdd_name,
                tdd_description=tdd_description,
                tdd_version=version,
                tdd_status=status,
                tdd_author=author,
                technical_components=tech_components,
                design_decisions=design_decisions,
                tdd_dependencies=dependencies,
                architecture_pattern=arch_pattern,
                security_considerations=security,
                performance_requirements=performance,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            # Register relationship
            rel_mgr.register_tdd(tdd_id, epic_id, dev_est_id, tdd_name)

            return TransformationResult(
                success=True,
                entity=tdd,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            errors.append(
                TransformationError(
                    field_name="tdd",
                    message=f"Failed to transform TDD: {str(e)}",
                    severity="error",
                )
            )
            return TransformationResult(
                success=False,
                entity=None,
                errors=errors,
                warnings=warnings,
            )

    def _extract_technical_components(
        self, extracted: ExtractedData, mapping: Dict[str, str]
    ) -> List[str]:
        """Extract technical components from document."""
        components = []

        # Try mapping first
        mapped_value = self._get_mapped_value(extracted, mapping, "technical_components")
        if mapped_value:
            if isinstance(mapped_value, list):
                return mapped_value
            if isinstance(mapped_value, str):
                import json
                try:
                    parsed = json.loads(mapped_value)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass
                # Comma-separated
                if "," in mapped_value:
                    return [c.strip() for c in mapped_value.split(",") if c.strip()]

        # Search in content for known technologies
        known_tech = [
            "Python", "FastAPI", "Django", "Flask",
            "JavaScript", "TypeScript", "React", "Vue", "Angular", "Node.js", "NestJS",
            "Java", "Spring Boot", "Spring Security",
            "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
            "Kafka", "RabbitMQ", "AWS", "GCP", "Azure",
            "Docker", "Kubernetes", "GraphQL", "REST",
        ]

        content_lower = extracted.raw_content.lower()
        for tech in known_tech:
            if tech.lower() in content_lower:
                components.append(tech)

        return list(set(components))[:10]  # Limit to 10

    def _extract_dependencies(
        self, extracted: ExtractedData, mapping: Dict[str, str]
    ) -> List[str]:
        """Extract service/system dependencies."""
        deps = []

        # Try mapping
        mapped_value = self._get_mapped_value(extracted, mapping, "tdd_dependencies")
        if mapped_value:
            if isinstance(mapped_value, list):
                return mapped_value
            if isinstance(mapped_value, str):
                import json
                try:
                    parsed = json.loads(mapped_value)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass
                if "," in mapped_value:
                    return [d.strip() for d in mapped_value.split(",") if d.strip()]

        # Look for dependency section
        for section_name, content in extracted.raw_sections.items():
            if "depend" in section_name.lower():
                # Extract list items
                import re
                items = re.findall(r"[-•]\s*(.+)", content)
                deps.extend([item.strip() for item in items if item.strip()])

        # Look for service patterns in content
        import re
        service_patterns = re.findall(r"\b(\w+-service)\b", extracted.raw_content)
        deps.extend(service_patterns)

        return list(set(deps))[:10]

    def _detect_architecture_pattern(self, content: str) -> str:
        """Detect architecture pattern from content."""
        patterns = {
            "Event Sourcing": ["event sourcing", "event store"],
            "CQRS": ["cqrs", "command query"],
            "Microservices": ["microservice", "service mesh"],
            "Adapter Pattern": ["adapter pattern", "pluggable"],
            "Repository Pattern": ["repository pattern"],
            "Saga Pattern": ["saga pattern", "distributed transaction"],
            "API Gateway": ["api gateway"],
            "Event-Driven": ["event-driven", "event driven"],
        }

        content_lower = content.lower()
        for pattern_name, keywords in patterns.items():
            if any(kw in content_lower for kw in keywords):
                return pattern_name

        return ""
