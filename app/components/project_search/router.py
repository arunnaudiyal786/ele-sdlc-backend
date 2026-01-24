"""
Project Search Router

API endpoints for searching and loading project documents.
"""

import logging
from fastapi import APIRouter, HTTPException, status

from app.rag.hybrid_search import HybridSearchService
from app.services.context_assembler import ContextAssembler
from app.services.project_indexer import ProjectMetadata
from .models import (
    FindMatchesRequest,
    FindMatchesResponse,
    SelectAndLoadRequest,
    SelectAndLoadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/project-search", tags=["project-search"])


@router.post(
    "/find-matches",
    response_model=FindMatchesResponse,
    summary="Find Similar Projects",
    description="""
    Search for similar historical projects using hybrid search (semantic + keyword).

    Returns top 5 matching projects with scores and metadata.
    User can then select 3 projects to load full documents.
    """,
)
async def find_matches(request: FindMatchesRequest) -> FindMatchesResponse:
    """
    Find similar projects using hybrid search

    **Flow:**
    1. User submits requirement text
    2. System searches project_index collection
    3. Returns top 5 matches with scores
    4. User selects 3 for full document loading

    **Example Request:**
    ```json
    {
        "requirement_text": "Real-time inventory tracking with barcode scanning",
        "top_k": 5
    }
    ```

    **Example Response:**
    ```json
    {
        "matches": [
            {
                "project_id": "PRJ-10051",
                "project_name": "Inventory Sync Automation",
                "summary": "This document describes...",
                "match_score": 0.87,
                "score_breakdown": {
                    "semantic_score": 0.85,
                    "keyword_score": 0.92
                },
                "folder_path": "data/raw/projects/PRJ-10051-inventory-sync-automation"
            }
        ],
        "total_matches": 5
    }
    ```
    """
    try:
        logger.info(
            f"Searching for similar projects: {request.requirement_text[:100]}..."
        )

        # Get hybrid search service
        search_service = HybridSearchService.get_instance()

        # Search project_index
        matches = await search_service.search_projects(
            query=request.requirement_text, top_k=request.top_k
        )

        logger.info(f"Found {len(matches)} matching projects")

        return FindMatchesResponse(matches=matches, total_matches=len(matches))

    except Exception as e:
        logger.error(f"Error finding matches: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search projects: {str(e)}",
        )


@router.post(
    "/select-and-load",
    response_model=SelectAndLoadResponse,
    summary="Load Selected Projects",
    description="""
    Load full documents (TDD, Estimation, Jira Stories) for selected projects.

    Parses all documents and returns structured JSON data ready for agents.
    """,
)
async def select_and_load(request: SelectAndLoadRequest) -> SelectAndLoadResponse:
    """
    Load full documents for selected projects

    **Flow:**
    1. User selects 3 projects from find-matches results
    2. System loads and parses all documents (TDD.docx, estimation.xlsx, jira_stories.xlsx)
    3. Returns structured JSON data for each project

    **Example Request:**
    ```json
    {
        "selected_project_ids": ["PRJ-10051", "PRJ-10052", "PRJ-10053"],
        "project_metadata": [...]  // From find-matches response
    }
    ```

    **Example Response:**
    ```json
    {
        "loaded_projects": {
            "PRJ-10051": {
                "tdd": {
                    "project_id": "PRJ-10051",
                    "epic_description": "...",
                    "module_list": [...],
                    "design_patterns": [...]
                },
                "estimation": {
                    "total_dev_points": 160.0,
                    "total_qa_points": 90.0,
                    "task_breakdown": [...]
                },
                "jira_stories": {
                    "stories": [...]
                }
            }
        },
        "projects_count": 3
    }
    ```
    """
    try:
        logger.info(
            f"Loading documents for {len(request.selected_project_ids)} projects"
        )

        # Convert ProjectMatch objects to ProjectMetadata
        metadata_list = []
        for match in request.project_metadata:
            # Only process selected projects
            if match.project_id in request.selected_project_ids:
                metadata = ProjectMetadata(
                    project_id=match.project_id,
                    project_name=match.project_name,
                    summary=match.summary,
                    folder_path=match.folder_path,
                    tdd_path=match.tdd_path,
                    estimation_path=match.estimation_path,
                    jira_stories_path=match.jira_stories_path,
                )
                metadata_list.append(metadata)

        # Load full documents
        assembler = ContextAssembler()
        loaded_projects = await assembler.load_full_documents(
            project_ids=request.selected_project_ids, project_metadata=metadata_list
        )

        # Convert to dict for response
        loaded_projects_dict = {
            project_id: docs.model_dump()
            for project_id, docs in loaded_projects.items()
        }

        logger.info(f"Successfully loaded {len(loaded_projects_dict)} projects")

        return SelectAndLoadResponse(
            loaded_projects=loaded_projects_dict,
            projects_count=len(loaded_projects_dict),
        )

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project files not found: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error loading projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load projects: {str(e)}",
        )
