from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime


class StoryItem(BaseModel):
    """Single Jira story."""
    title: str
    story_type: str = Field(..., pattern="^(Story|Task|Bug|Spike)$")
    story_points: int = Field(..., ge=1, le=13)
    acceptance_criteria: List[str]
    priority: str = Field(..., pattern="^(HIGH|MEDIUM|LOW)$")


class StoriesRequest(BaseModel):
    """Request to generate Jira stories."""
    session_id: str
    requirement_text: str
    selected_matches: List[Dict]
    modules_output: Dict
    effort_output: Dict


class StoriesResponse(BaseModel):
    """Response with generated stories."""
    session_id: str
    agent: str = "stories"
    stories: List[StoryItem]
    total_stories: int
    total_story_points: int
    generated_at: datetime
