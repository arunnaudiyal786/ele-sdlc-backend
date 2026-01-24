from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime


class ModuleItem(BaseModel):
    """Single module in impact analysis."""
    name: str
    impact: str = Field(..., pattern="^(HIGH|MEDIUM|LOW)$")
    reason: str


class ImpactedModulesRequest(BaseModel):
    """Request to identify impacted modules."""
    session_id: str
    requirement_text: str
    selected_matches: List[Dict]  # Kept for backward compatibility
    loaded_projects: Dict[str, Dict] = Field(default_factory=dict)  # Full documents from selected projects


class ImpactedModulesResponse(BaseModel):
    """Response with identified impacted modules."""
    session_id: str
    agent: str = "impacted_modules"
    functional_modules: List[ModuleItem]
    technical_modules: List[ModuleItem]
    total_modules: int
    generated_at: datetime
