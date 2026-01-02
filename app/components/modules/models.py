from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime


class ModuleItem(BaseModel):
    """Single module in impact analysis."""
    name: str
    impact: str = Field(..., pattern="^(HIGH|MEDIUM|LOW)$")
    reason: str


class ModulesRequest(BaseModel):
    """Request to identify impacted modules."""
    session_id: str
    requirement_text: str
    selected_matches: List[Dict]


class ModulesResponse(BaseModel):
    """Response with identified modules."""
    session_id: str
    agent: str = "modules"
    functional_modules: List[ModuleItem]
    technical_modules: List[ModuleItem]
    total_modules: int
    generated_at: datetime
