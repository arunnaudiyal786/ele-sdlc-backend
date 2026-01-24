import json
from datetime import datetime
from typing import Dict, List
from app.components.base.component import BaseComponent
from app.components.base.exceptions import ResponseParsingError
from app.utils.ollama_client import get_ollama_client
from app.utils.json_repair import parse_llm_json
from app.utils.audit import AuditTrailManager
from .models import JiraStoriesRequest, JiraStoriesResponse, JiraStoryItem
from .prompts import JIRA_STORIES_SYSTEM_PROMPT, JIRA_STORIES_USER_PROMPT


class JiraStoriesService(BaseComponent[JiraStoriesRequest, JiraStoriesResponse]):
    """Jira stories generation agent as a component."""

    # Map LLM variations to valid story_type values
    STORY_TYPE_MAPPING = {
        "STORY": "Story",
        "TASK": "Task",
        "BUG": "Bug",
        "SPIKE": "Spike",
        "FEATURE": "Story",  # Feature -> Story
        "USER STORY": "Story",
        "TECHNICAL TASK": "Task",
        "INVESTIGATION": "Spike",
        "RESEARCH": "Spike",
        "DEFECT": "Bug",
        "BUGFIX": "Bug",
    }

    def __init__(self):
        self.ollama = get_ollama_client()

    @property
    def component_name(self) -> str:
        return "jira_stories"

    async def process(self, request: JiraStoriesRequest) -> JiraStoriesResponse:
        """Generate Jira stories using LLM."""
        modules_summary = self._format_modules(request.impacted_modules_output)
        effort_summary = self._format_effort(request.estimation_effort_output)
        tdd_summary = self._format_tdd(request.tdd_output)

        user_prompt = JIRA_STORIES_USER_PROMPT.format(
            requirement_description=request.requirement_text,
            modules_summary=modules_summary,
            tdd_summary=tdd_summary,
            effort_summary=effort_summary,
        )

        audit = AuditTrailManager(request.session_id)
        audit.save_text("input_prompt.txt", f"{JIRA_STORIES_SYSTEM_PROMPT}\n\n{user_prompt}", subfolder="step3_agents/agent_jira_stories")

        raw_response, llm_metadata = await self.ollama.generate(
            system_prompt=JIRA_STORIES_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json",
        )

        # Save LLM request metadata
        audit.save_json("llm_request.json", llm_metadata.to_dict(), subfolder="step3_agents/agent_jira_stories")
        audit.save_text("raw_response.txt", raw_response, subfolder="step3_agents/agent_jira_stories")

        parsed = self._parse_response(raw_response)
        stories = [JiraStoryItem(**self._normalize_story(s)) for s in parsed.get("stories", [])]
        total_points = sum(s.story_points for s in stories)

        response = JiraStoriesResponse(
            session_id=request.session_id,
            stories=stories,
            story_count=len(stories),
            total_story_points=total_points,
            generated_at=datetime.now(),
        )

        audit.save_json("parsed_output.json", response.model_dump(), subfolder="step3_agents/agent_jira_stories")
        audit.add_step_completed("jira_stories_generated")

        return response

    def _format_modules(self, modules_output: Dict) -> str:
        """Format modules for prompt."""
        lines = []
        for m in modules_output.get("functional_modules", [])[:5]:
            lines.append(f"- {m.get('name')}")
        for m in modules_output.get("technical_modules", [])[:5]:
            lines.append(f"- {m.get('name')}")
        return "\n".join(lines) if lines else "No modules."

    def _format_effort(self, effort_output: Dict) -> str:
        """Format effort for prompt."""
        return f"Dev: {effort_output.get('total_dev_hours', 0)}h, QA: {effort_output.get('total_qa_hours', 0)}h, Points: {effort_output.get('story_points', 0)}"

    def _format_tdd(self, tdd_output: Dict) -> str:
        """Format TDD for prompt."""
        if not tdd_output:
            return "No TDD available."
        return f"Architecture: {tdd_output.get('architecture_pattern', 'N/A')}, Components: {', '.join(tdd_output.get('technical_components', [])[:5])}"

    def _normalize_story(self, story: Dict) -> Dict:
        """Normalize story data from LLM to handle type variations.

        The LLM sometimes generates invalid story_type values like 'Feature'.
        This method maps them to valid values: Story, Task, Bug, Spike.
        """
        normalized = story.copy()

        # Normalize story_type
        if "story_type" in normalized:
            story_type = str(normalized["story_type"]).upper()
            normalized["story_type"] = self.STORY_TYPE_MAPPING.get(story_type, "Story")
        else:
            normalized["story_type"] = "Story"  # Default if missing

        # Normalize priority if present
        if "priority" in normalized:
            priority = str(normalized["priority"]).upper()
            if priority not in ["HIGH", "MEDIUM", "LOW"]:
                normalized["priority"] = "MEDIUM"  # Default to MEDIUM
        else:
            normalized["priority"] = "MEDIUM"

        # Ensure story_points is valid (1-13)
        if "story_points" in normalized:
            points = normalized["story_points"]
            if not isinstance(points, int) or points < 1:
                normalized["story_points"] = 3
            elif points > 13:
                normalized["story_points"] = 13
        else:
            normalized["story_points"] = 3  # Default

        # Ensure required lists exist
        if "acceptance_criteria" not in normalized or not isinstance(normalized["acceptance_criteria"], list):
            normalized["acceptance_criteria"] = ["Acceptance criteria to be defined"]

        if "labels" not in normalized or not isinstance(normalized["labels"], list):
            normalized["labels"] = []

        return normalized

    def _parse_response(self, raw: str) -> Dict:
        """Parse LLM JSON response with automatic repair."""
        try:
            return parse_llm_json(raw, component_name="jira_stories")
        except json.JSONDecodeError as e:
            raise ResponseParsingError(f"Failed to parse: {e}", component="jira_stories")
