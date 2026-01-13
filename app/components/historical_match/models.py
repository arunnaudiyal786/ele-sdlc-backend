from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class HistoricalMatchRequest(BaseModel):
    """Request to search for historical matches."""
    session_id: str
    query: str
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    max_results: int = Field(default=10, ge=1, le=50)


class MatchResult(BaseModel):
    """Single match result."""
    match_id: str
    epic_id: str
    epic_name: str
    description: str
    match_score: float
    score_breakdown: Dict[str, float]
    technologies: List[str] = []
    actual_hours: Optional[int] = None
    estimated_hours: Optional[int] = None


class HistoricalMatchResponse(BaseModel):
    """Historical match results response."""
    session_id: str
    total_matches: int
    matches: List[MatchResult]
    search_time_ms: int


class MatchSelectionRequest(BaseModel):
    """Request to select matches for impact analysis."""
    session_id: str
    selected_match_ids: List[str]


class MatchSelectionResponse(BaseModel):
    """Response after selecting matches."""
    session_id: str
    selected_count: int
    status: str
