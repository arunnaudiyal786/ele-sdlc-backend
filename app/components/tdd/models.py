from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class TDDRequest(BaseModel):
    """Request to generate TDD document."""
    session_id: str
    requirement_text: str
    selected_matches: List[Dict]
    impacted_modules_output: Dict
    estimation_effort_output: Dict


class TDDResponse(BaseModel):
    """Response with generated TDD document."""
    session_id: str
    agent: str = "tdd"
    tdd_name: str
    tdd_description: str
    technical_components: List[str]
    design_decisions: str
    architecture_pattern: str
    security_considerations: str
    performance_requirements: str
    tdd_dependencies: List[str]
    markdown_content: str
    markdown_file_path: Optional[str] = None
    generated_at: datetime
