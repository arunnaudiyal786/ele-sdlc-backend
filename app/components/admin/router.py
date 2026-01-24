"""
Admin Router

API endpoints for administrative tasks (index management).
"""

import logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, BackgroundTasks

from app.components.base.config import get_settings
from app.services.project_indexer import ProjectIndexer
from .models import (
    RebuildIndexResponse,
    AddProjectRequest,
    AddProjectResponse,
    IndexStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/index/rebuild",
    response_model=RebuildIndexResponse,
    summary="Rebuild Project Index",
    description="""
    Rebuild the entire project index from scratch.

    Scans data/raw/projects/ folder and re-indexes all projects.
    Runs in the background and returns immediately.
    """,
)
async def rebuild_index(background_tasks: BackgroundTasks) -> RebuildIndexResponse:
    """
    Rebuild project index from scratch

    **Warning:** This deletes the existing index and rebuilds from source files.

    **Flow:**
    1. Delete existing project_index collection
    2. Scan data/raw/projects/ folder
    3. Extract metadata from each project's TDD file
    4. Index all projects in ChromaDB

    **Example Response:**
    ```json
    {
        "status": "started",
        "message": "Index rebuild started in background",
        "projects_indexed": 0
    }
    ```

    **Note:** Check logs for progress. The rebuild runs asynchronously.
    """
    try:
        logger.info("Starting project index rebuild")

        # Get project base path
        base_path = Path("data/raw/projects")

        if not base_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Projects directory not found: {base_path}",
            )

        # Get indexer instance
        indexer = ProjectIndexer.get_instance()

        # Run rebuild synchronously (for now - can be made async later)
        projects_indexed = await indexer.build_index(base_path)

        logger.info(f"Index rebuild completed: {projects_indexed} projects indexed")

        return RebuildIndexResponse(
            status="completed",
            message=f"Successfully indexed {projects_indexed} projects",
            projects_indexed=projects_indexed,
        )

    except Exception as e:
        logger.error(f"Index rebuild failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Index rebuild failed: {str(e)}",
        )


@router.post(
    "/index/add-project",
    response_model=AddProjectResponse,
    summary="Add Project to Index",
    description="""
    Add a single project to the index.

    Useful for incrementally adding new projects without full rebuild.
    """,
)
async def add_project(request: AddProjectRequest) -> AddProjectResponse:
    """
    Add single project to index

    **Flow:**
    1. Verify project folder exists
    2. Extract metadata from TDD file
    3. Add to project_index collection

    **Example Request:**
    ```json
    {
        "project_folder": "data/raw/projects/PRJ-10056-new-project"
    }
    ```

    **Example Response:**
    ```json
    {
        "status": "success",
        "project_id": "PRJ-10056",
        "message": "Project PRJ-10056 added to index"
    }
    ```
    """
    try:
        project_path = Path(request.project_folder)

        if not project_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project folder not found: {request.project_folder}",
            )

        logger.info(f"Adding project to index: {project_path}")

        # Get indexer instance
        indexer = ProjectIndexer.get_instance()

        # Add project
        project_id = await indexer.add_project(project_path)

        logger.info(f"Project added: {project_id}")

        return AddProjectResponse(
            status="success",
            project_id=project_id,
            message=f"Project {project_id} added to index",
        )

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to add project: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add project: {str(e)}",
        )


@router.get(
    "/index/status",
    response_model=IndexStatusResponse,
    summary="Get Index Status",
    description="""
    Get statistics about the project index.

    Returns total number of projects and index metadata.
    """,
)
async def index_status() -> IndexStatusResponse:
    """
    Get index statistics

    **Example Response:**
    ```json
    {
        "collection_name": "project_index",
        "total_projects": 5,
        "chroma_persist_dir": "./data/chroma",
        "last_checked": "2026-01-24T10:30:00"
    }
    ```
    """
    try:
        settings = get_settings()

        # Get indexer to access vector store
        indexer = ProjectIndexer.get_instance()

        # Get collection
        collection = indexer.vector_store.get_or_create_collection("project_index")

        # Count documents
        total_projects = collection.count()

        return IndexStatusResponse(
            collection_name="project_index",
            total_projects=total_projects,
            chroma_persist_dir=settings.chroma_persist_dir,
            last_checked=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Failed to get index status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get index status: {str(e)}",
        )
