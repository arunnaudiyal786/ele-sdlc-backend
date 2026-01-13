from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime


class JiraStoryItem(BaseModel):
    """Single Jira story."""
    title: str
    story_type: str = Field(..., pattern="^(Story|Task|Bug|Spike)$")
    story_points: int = Field(..., ge=1, le=13)
    acceptance_criteria: List[str]
    priority: str = Field(..., pattern="^(HIGH|MEDIUM|LOW)$")


class JiraStoriesRequest(BaseModel):
    """Request to generate Jira stories."""
    session_id: str
    requirement_text: str
    selected_matches: List[Dict]
    impacted_modules_output: Dict
    estimation_effort_output: Dict
    tdd_output: Dict


class JiraStoriesResponse(BaseModel):
    """Response with generated Jira stories."""
    session_id: str
    agent: str = "jira_stories"
    stories: List[JiraStoryItem]
    total_stories: int
    total_story_points: int
    generated_at: datetime
