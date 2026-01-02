from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime


class RiskItem(BaseModel):
    """Single risk with mitigation."""
    title: str
    description: str
    severity: str = Field(..., pattern="^(HIGH|MEDIUM|LOW)$")
    likelihood: str = Field(..., pattern="^(HIGH|MEDIUM|LOW)$")
    category: str
    mitigation: str


class RisksRequest(BaseModel):
    """Request for risk identification."""
    session_id: str
    requirement_text: str
    selected_matches: List[Dict]
    modules_output: Dict
    effort_output: Dict
    code_impact_output: Dict


class RisksResponse(BaseModel):
    """Response with identified risks."""
    session_id: str
    agent: str = "risks"
    risks: List[RiskItem]
    total_risks: int
    high_severity_count: int
    generated_at: datetime
