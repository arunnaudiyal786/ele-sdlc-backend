from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class SessionCreateRequest(BaseModel):
    """Request to create a new assessment session."""
    user_id: Optional[str] = None


class SessionResponse(BaseModel):
    """Session details response."""
    session_id: str
    created_at: datetime
    status: str
    audit_path: str
    user_id: Optional[str] = None


class SessionAuditResponse(BaseModel):
    """Full audit trail for a session."""
    session_id: str
    created_at: datetime
    status: str
    steps_completed: List[str]
    timing: Dict[str, int]
    data: Dict


class SessionSummaryItem(BaseModel):
    """Summary of a single session for list view."""
    session_id: str
    created_at: datetime
    status: str
    requirement_text: Optional[str] = None  # First 200 chars
    jira_epic_id: Optional[str] = None
    total_story_points: Optional[int] = None
    total_hours: Optional[int] = None


class SessionListResponse(BaseModel):
    """Response for listing sessions."""
    sessions: List[SessionSummaryItem]
    total: int
    limit: int
    offset: int
