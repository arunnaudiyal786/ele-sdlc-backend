from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime


class EffortBreakdown(BaseModel):
    """Effort breakdown by category."""
    category: str
    dev_hours: int
    qa_hours: int
    description: str


class EffortRequest(BaseModel):
    """Request for effort estimation."""
    session_id: str
    requirement_text: str
    selected_matches: List[Dict]
    modules_output: Dict


class EffortResponse(BaseModel):
    """Response with effort estimation."""
    session_id: str
    agent: str = "effort"
    total_dev_hours: int
    total_qa_hours: int
    total_hours: int
    story_points: int
    confidence: str = Field(..., pattern="^(HIGH|MEDIUM|LOW)$")
    breakdown: List[EffortBreakdown]
    generated_at: datetime
