from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RequirementSubmitRequest(BaseModel):
    """Request to submit a requirement."""
    session_id: str
    requirement_description: str = Field(..., min_length=20)
    jira_epic_id: Optional[str] = None


class RequirementResponse(BaseModel):
    """Response after requirement submission."""
    session_id: str
    requirement_id: str
    status: str
    character_count: int
    extracted_keywords: List[str]
    created_at: datetime
