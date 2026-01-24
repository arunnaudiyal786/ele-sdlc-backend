"""
Admin API Models

Request/Response models for admin endpoints (index management).
"""

from pydantic import BaseModel, Field
from datetime import datetime


# ===== Index Rebuild =====

class RebuildIndexResponse(BaseModel):
    """Response for index rebuild request"""

    status: str = Field(..., description="Status: started, completed, or failed")
    message: str = Field(..., description="Status message")
    projects_indexed: int = Field(default=0, description="Number of projects indexed")


# ===== Add Project =====

class AddProjectRequest(BaseModel):
    """Request to add single project to index"""

    project_folder: str = Field(
        ...,
        description="Path to project folder",
        examples=["data/raw/projects/PRJ-10056-new-project"],
    )


class AddProjectResponse(BaseModel):
    """Response for add project request"""

    status: str = Field(..., description="Status: success or failed")
    project_id: str = Field(..., description="ID of added project")
    message: str = Field(..., description="Status message")


# ===== Index Status =====

class IndexStatusResponse(BaseModel):
    """Response with index statistics"""

    collection_name: str = Field(..., description="Collection name (project_index)")
    total_projects: int = Field(..., description="Number of projects in index")
    chroma_persist_dir: str = Field(..., description="ChromaDB persistence directory")
    last_checked: datetime = Field(..., description="Timestamp of status check")
