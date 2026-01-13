import json
from datetime import datetime
from typing import Dict, List
from app.components.base.component import BaseComponent
from app.components.base.exceptions import ResponseParsingError
from app.utils.ollama_client import get_ollama_client
from app.utils.audit import AuditTrailManager
from .models import EstimationEffortRequest, EstimationEffortResponse, EffortBreakdown
from .prompts import ESTIMATION_EFFORT_SYSTEM_PROMPT, ESTIMATION_EFFORT_USER_PROMPT


class EstimationEffortService(BaseComponent[EstimationEffortRequest, EstimationEffortResponse]):
    """Estimation effort agent as a component."""

    def __init__(self):
        self.ollama = get_ollama_client()

    @property
    def component_name(self) -> str:
        return "estimation_effort"

    async def process(self, request: EstimationEffortRequest) -> EstimationEffortResponse:
        """Estimate effort using LLM."""
        modules_summary = self._format_modules(request.impacted_modules_output)
        formatted_matches = self._format_matches(request.selected_matches)

        user_prompt = ESTIMATION_EFFORT_USER_PROMPT.format(
            requirement_description=request.requirement_text,
            modules_summary=modules_summary,
            formatted_historical_matches=formatted_matches,
        )

        audit = AuditTrailManager(request.session_id)
        audit.save_text("input_prompt.txt", f"{ESTIMATION_EFFORT_SYSTEM_PROMPT}\n\n{user_prompt}", subfolder="step3_agents/agent_estimation_effort")

        raw_response = await self.ollama.generate(
            system_prompt=ESTIMATION_EFFORT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json",
        )

        audit.save_text("raw_response.txt", raw_response, subfolder="step3_agents/agent_estimation_effort")

        parsed = self._parse_response(raw_response)
        breakdown = [EffortBreakdown(**b) for b in parsed.get("breakdown", [])]

        response = EstimationEffortResponse(
            session_id=request.session_id,
            total_dev_hours=parsed.get("total_dev_hours", 0),
            total_qa_hours=parsed.get("total_qa_hours", 0),
            total_hours=parsed.get("total_dev_hours", 0) + parsed.get("total_qa_hours", 0),
            story_points=parsed.get("story_points", 0),
            confidence=parsed.get("confidence", "MEDIUM"),
            breakdown=breakdown,
            generated_at=datetime.now(),
        )

        audit.save_json("parsed_output.json", response.model_dump(), subfolder="step3_agents/agent_estimation_effort")
        audit.add_step_completed("estimation_effort_completed")

        return response

    def _format_modules(self, modules_output: Dict) -> str:
        """Format modules for prompt."""
        lines = []
        for m in modules_output.get("functional_modules", [])[:5]:
            lines.append(f"- {m.get('name')} ({m.get('impact')})")
        for m in modules_output.get("technical_modules", [])[:5]:
            lines.append(f"- {m.get('name')} ({m.get('impact')})")
        return "\n".join(lines) if lines else "No modules identified."

    def _format_matches(self, matches: List[Dict]) -> str:
        """Format matches for prompt."""
        lines = []
        for m in matches[:3]:
            hours = m.get("actual_hours") or m.get("estimated_hours") or "N/A"
            lines.append(f"- {m.get('epic_name', 'Unknown')}: {hours} hours")
        return "\n".join(lines) if lines else "No historical data."

    def _parse_response(self, raw: str) -> Dict:
        """Parse LLM JSON response."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ResponseParsingError(f"Failed to parse: {e}", component="estimation_effort")
