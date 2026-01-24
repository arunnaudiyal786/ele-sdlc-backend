from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime


class EffortBreakdown(BaseModel):
    """Effort breakdown by category."""
    category: str
    dev_hours: int
    qa_hours: int
    description: str


class EstimationEffortRequest(BaseModel):
    """Request for estimation effort."""
    session_id: str
    requirement_text: str
    selected_matches: List[Dict]  # Kept for backward compatibility
    impacted_modules_output: Dict
    loaded_projects: Dict[str, Dict] = Field(default_factory=dict)  # Full documents from selected projects


class EstimationEffortResponse(BaseModel):
    """Response with estimation effort."""
    session_id: str
    agent: str = "estimation_effort"
    total_dev_hours: int
    total_qa_hours: int
    total_hours: int
    story_points: int
    confidence: str = Field(..., pattern="^(HIGH|MEDIUM|LOW)$")
    breakdown: List[EffortBreakdown]
    generated_at: datetime
