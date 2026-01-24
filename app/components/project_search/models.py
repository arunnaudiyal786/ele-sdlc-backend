"""
Project Search API Models

Request/Response models for project search endpoints.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field

from app.rag.hybrid_search import ProjectMatch, ScoreBreakdown


# ===== Find Matches Endpoint =====

class FindMatchesRequest(BaseModel):
    """Request to find similar projects"""

    requirement_text: str = Field(
        ...,
        description="User requirement text to search for similar projects",
        min_length=10,
        examples=["Real-time inventory tracking system with barcode scanning"],
    )
    top_k: int = Field(
        default=5,
        description="Number of top matches to return",
        ge=1,
        le=10,
    )


class FindMatchesResponse(BaseModel):
    """Response with top matching projects"""

    matches: List[ProjectMatch] = Field(
        ..., description="List of matching projects with scores"
    )
    total_matches: int = Field(..., description="Total number of matches returned")


# ===== Select and Load Endpoint =====

class SelectAndLoadRequest(BaseModel):
    """Request to load full documents for selected projects"""

    selected_project_ids: List[str] = Field(
        ...,
        description="List of selected project IDs (typically 3)",
        min_length=1,
        max_length=5,
        examples=[["PRJ-10051", "PRJ-10052", "PRJ-10053"]],
    )
    project_metadata: List[ProjectMatch] = Field(
        ...,
        description="Metadata from find-matches response (contains file paths)",
    )


class SelectAndLoadResponse(BaseModel):
    """Response with loaded project documents"""

    loaded_projects: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Map of project_id to full document data (TDD, Estimation, Jira)",
    )
    projects_count: int = Field(..., description="Number of projects loaded")
