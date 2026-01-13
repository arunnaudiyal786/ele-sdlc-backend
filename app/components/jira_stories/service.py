import json
from datetime import datetime
from typing import Dict, List
from app.components.base.component import BaseComponent
from app.components.base.exceptions import ResponseParsingError
from app.utils.ollama_client import get_ollama_client
from app.utils.audit import AuditTrailManager
from .models import JiraStoriesRequest, JiraStoriesResponse, JiraStoryItem
from .prompts import JIRA_STORIES_SYSTEM_PROMPT, JIRA_STORIES_USER_PROMPT


class JiraStoriesService(BaseComponent[JiraStoriesRequest, JiraStoriesResponse]):
    """Jira stories generation agent as a component."""

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

        raw_response = await self.ollama.generate(
            system_prompt=JIRA_STORIES_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json",
        )

        audit.save_text("raw_response.txt", raw_response, subfolder="step3_agents/agent_jira_stories")

        parsed = self._parse_response(raw_response)
        stories = [JiraStoryItem(**s) for s in parsed.get("stories", [])]
        total_points = sum(s.story_points for s in stories)

        response = JiraStoriesResponse(
            session_id=request.session_id,
            stories=stories,
            total_stories=len(stories),
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

    def _parse_response(self, raw: str) -> Dict:
        """Parse LLM JSON response."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ResponseParsingError(f"Failed to parse: {e}", component="jira_stories")
