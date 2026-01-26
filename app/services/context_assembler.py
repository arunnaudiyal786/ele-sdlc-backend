"""
Context Assembler Service

Loads full documents for selected projects and assembles agent-specific context.
Each agent receives different subsets of document data optimized for its purpose.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any

from pydantic import BaseModel, Field

from app.services.project_indexer import ProjectMetadata
from app.services.parsers import (
    TDDParser,
    EstimationParser,
    JiraStoriesParser,
    TDDDocument,
    EstimationDocument,
    JiraStoriesDocument,
)

logger = logging.getLogger(__name__)


# ===== Pydantic Models =====

class ProjectDocuments(BaseModel):
    """Complete set of documents for a single project"""

    project_id: str = Field(..., description="Project ID")
    tdd: TDDDocument = Field(..., description="Parsed TDD document")
    estimation: EstimationDocument = Field(..., description="Parsed estimation document")
    jira_stories: JiraStoriesDocument = Field(..., description="Parsed Jira stories")


# ===== Context Assembler =====

class ContextAssembler:
    """
    Assembles agent-specific context from full documents.

    Flow:
    1. Load full documents for selected projects (3 projects)
    2. Assemble context specific to each agent's needs
    3. Return structured JSON context for agent processing
    """

    def __init__(self):
        self.tdd_parser = TDDParser()
        self.estimation_parser = EstimationParser()
        self.jira_stories_parser = JiraStoriesParser()

    async def load_full_documents(
        self,
        project_ids: List[str],
        project_metadata: List[ProjectMetadata],
    ) -> Dict[str, ProjectDocuments]:
        """
        Load full documents for selected projects

        Args:
            project_ids: List of selected project IDs (e.g., ["PRJ-10051", "PRJ-10052", "PRJ-10053"])
            project_metadata: Metadata from search results (contains file paths)

        Returns:
            Dict mapping project_id → ProjectDocuments

        Raises:
            FileNotFoundError: If required files are missing
            ValueError: If parsing fails
        """
        logger.info(f"Loading full documents for {len(project_ids)} projects")

        loaded_docs: Dict[str, ProjectDocuments] = {}

        # Create lookup dict for metadata
        metadata_map = {m.project_id: m for m in project_metadata}

        for project_id in project_ids:
            # Find metadata for this project
            if project_id not in metadata_map:
                logger.error(f"Metadata not found for project: {project_id}")
                continue

            metadata = metadata_map[project_id]

            try:
                # Parse all documents
                logger.info(f"Parsing documents for {project_id}")

                tdd = await self.tdd_parser.parse(Path(metadata.tdd_path))
                estimation = await self.estimation_parser.parse(Path(metadata.estimation_path))
                jira_stories = await self.jira_stories_parser.parse(Path(metadata.jira_stories_path))

                loaded_docs[project_id] = ProjectDocuments(
                    project_id=project_id,
                    tdd=tdd,
                    estimation=estimation,
                    jira_stories=jira_stories,
                )

                logger.info(f"✅ Loaded documents for {project_id}")

            except Exception as e:
                logger.error(f"Failed to load documents for {project_id}: {e}")
                raise

        logger.info(f"Successfully loaded {len(loaded_docs)} project document sets")
        return loaded_docs

    async def assemble_agent_context(
        self,
        agent_name: str,
        loaded_projects: Dict[str, ProjectDocuments],
        current_requirement: str,
        impacted_modules_output: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Assemble context specific to each agent

        Each agent receives different document subsets optimized for its purpose:
        - impacted_modules: TDD module data (module_list, interaction_flow, design_decisions, risks)
        - estimation_effort: Estimation data + filtered impacted modules (task_breakdown, total_points, impacted_modules)
        - tdd: Full TDD content (design_overview, design_patterns, module_designs, full_text)
        - jira_stories: Jira stories + estimation tasks (existing_stories, task_breakdown)

        Args:
            agent_name: Name of agent requesting context (e.g., "impacted_modules")
            loaded_projects: Dict of project_id → ProjectDocuments
            current_requirement: User's current requirement text
            impacted_modules_output: Optional output from impacted_modules agent (for estimation_effort)

        Returns:
            Structured context dict with current_requirement and similar_projects

        Context Format:
        {
            "current_requirement": str,
            "similar_projects": [
                {
                    "project_id": str,
                    "project_name": str,
                    "relevant_data": {...}  # Agent-specific data
                }
            ]
        }
        """
        logger.info(f"Assembling context for agent: {agent_name}")

        context = {
            "current_requirement": current_requirement,
            "similar_projects": [],
        }

        for project_id, docs in loaded_projects.items():
            # Assemble agent-specific data
            if agent_name == "impacted_modules":
                relevant_data = self._context_for_impacted_modules(docs)

            elif agent_name == "estimation_effort":
                relevant_data = self._context_for_estimation_effort(
                    docs, impacted_modules_output=impacted_modules_output
                )

            elif agent_name == "tdd":
                relevant_data = self._context_for_tdd(docs)

            elif agent_name == "jira_stories":
                relevant_data = self._context_for_jira_stories(docs)

            else:
                # Default: provide full context
                logger.warning(f"Unknown agent '{agent_name}', providing full context")
                relevant_data = {
                    "tdd": docs.tdd.model_dump(),
                    "estimation": docs.estimation.model_dump(),
                    "jira_stories": docs.jira_stories.model_dump(),
                }

            context["similar_projects"].append(
                {
                    "project_id": project_id,
                    "project_name": docs.tdd.project_name or project_id,
                    "relevant_data": relevant_data,
                }
            )

        logger.info(f"Assembled context with {len(context['similar_projects'])} reference projects")
        return context

    def _context_for_impacted_modules(self, docs: ProjectDocuments) -> Dict[str, Any]:
        """
        Context for Impacted Modules Agent

        Needs: Module information, interaction flows, design decisions, risks
        Source: TDD document
        """
        return {
            "epic_description": docs.tdd.epic_description,
            "module_list": [m.model_dump() for m in docs.tdd.module_list],
            "interaction_flow": docs.tdd.interaction_flow,
            "design_decisions": docs.tdd.design_decisions,
            "design_patterns": docs.tdd.design_patterns,
            "risks": docs.tdd.risks,
        }

    def _context_for_estimation_effort(
        self,
        docs: ProjectDocuments,
        impacted_modules_output: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Context for Estimation Effort Agent

        Needs: Task breakdowns, effort points, filtered impacted modules
        Source: Estimation document + impacted modules from analysis (not full TDD module list)

        Supports two estimation formats:
        1. NEW FORMAT: Single "Scope Estimation" sheet with total_points (no DEV/QA split)
        2. LEGACY FORMAT: Separate dev_points/qa_points columns

        Args:
            docs: Project documents
            impacted_modules_output: Output from impacted_modules agent containing
                                    functional_modules and technical_modules lists
        """
        # Extract impacted modules from analysis output
        # These are filtered modules relevant to the requirement, not full TDD module_list
        impacted_modules = []
        if impacted_modules_output:
            functional = impacted_modules_output.get("functional_modules", [])
            technical = impacted_modules_output.get("technical_modules", [])
            # Combine both types of impacted modules
            impacted_modules = functional + technical

        # Build context with full estimation data
        context = {
            "epic_description": docs.tdd.epic_description,
            "total_dev_points": docs.estimation.total_dev_points,
            "total_qa_points": docs.estimation.total_qa_points,
            "total_points": docs.estimation.total_points,  # Total effort (new format)
            "task_breakdown": [t.model_dump() for t in docs.estimation.task_breakdown],
            "impacted_modules": impacted_modules,  # Filtered modules, not full module_list
            "assumptions_and_risks": docs.estimation.assumptions_and_risks,
            "estimate_summary": docs.estimation.estimate_summary,
            "sizing_guidelines": docs.estimation.sizing_guidelines,
            # Include all_sheets for complete visibility to LLM
            "all_sheets": docs.estimation.all_sheets,
        }

        return context

    def _context_for_tdd(self, docs: ProjectDocuments) -> Dict[str, Any]:
        """
        Context for TDD Generation Agent

        Needs: Design patterns, technical architecture, module designs
        Source: Full TDD document
        """
        return {
            "epic_description": docs.tdd.epic_description,
            "scope": docs.tdd.scope,
            "design_overview": docs.tdd.design_overview,
            "design_patterns": docs.tdd.design_patterns,
            "design_decisions": docs.tdd.design_decisions,
            "module_list": [m.model_dump() for m in docs.tdd.module_list],
            "module_designs": [m.model_dump() for m in docs.tdd.module_designs],
            "interaction_flow": docs.tdd.interaction_flow,
            "full_tdd_text": docs.tdd.full_text,
        }

    def _context_for_jira_stories(self, docs: ProjectDocuments) -> Dict[str, Any]:
        """
        Context for Jira Stories Agent

        Needs: Existing story formats, task breakdowns for story generation
        Source: Jira stories document + Estimation task breakdown
        """
        return {
            "epic_description": docs.tdd.epic_description,
            "existing_stories": [s.model_dump() for s in docs.jira_stories.stories],
            "task_breakdown": [t.model_dump() for t in docs.estimation.task_breakdown],
            "total_dev_points": docs.estimation.total_dev_points,
            "total_qa_points": docs.estimation.total_qa_points,
        }
