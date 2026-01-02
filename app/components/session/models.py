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
