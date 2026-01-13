from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class CodeFile(BaseModel):
    """Single impacted code file."""
    file_path: str
    repository: str
    change_type: str = Field(..., pattern="^(CREATE|MODIFY|DELETE)$")
    language: str
    reason: str
    estimated_lines: Optional[int] = None


class CodeImpactRequest(BaseModel):
    """Request for code impact analysis."""
    session_id: str
    requirement_text: str
    selected_matches: List[Dict]
    impacted_modules_output: Dict
    jira_stories_output: Dict


class CodeImpactResponse(BaseModel):
    """Response with code impact analysis."""
    session_id: str
    agent: str = "code_impact"
    files: List[CodeFile]
    total_files: int
    repositories_affected: List[str]
    generated_at: datetime
