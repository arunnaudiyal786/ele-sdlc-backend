import json
from datetime import datetime
from typing import Dict
from app.components.base.component import BaseComponent
from app.components.base.exceptions import ResponseParsingError
from app.utils.ollama_client import get_ollama_client
from app.utils.audit import AuditTrailManager
from .models import RisksRequest, RisksResponse, RiskItem
from .prompts import RISKS_SYSTEM_PROMPT, RISKS_USER_PROMPT


class RisksService(BaseComponent[RisksRequest, RisksResponse]):
    """Risk identification agent as a component."""

    def __init__(self):
        self.ollama = get_ollama_client()

    @property
    def component_name(self) -> str:
        return "risks"

    async def process(self, request: RisksRequest) -> RisksResponse:
        """Identify risks using LLM."""
        modules_summary = self._format_modules(request.modules_output)
        effort_summary = self._format_effort(request.effort_output)
        code_summary = self._format_code(request.code_impact_output)

        user_prompt = RISKS_USER_PROMPT.format(
            requirement_description=request.requirement_text,
            modules_summary=modules_summary,
            effort_summary=effort_summary,
            code_summary=code_summary,
        )

        audit = AuditTrailManager(request.session_id)
        audit.save_text("input_prompt.txt", f"{RISKS_SYSTEM_PROMPT}\n\n{user_prompt}", subfolder="step3_agents/agent_risks")

        raw_response = await self.ollama.generate(
            system_prompt=RISKS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json",
        )

        audit.save_text("raw_response.txt", raw_response, subfolder="step3_agents/agent_risks")

        parsed = self._parse_response(raw_response)
        risks = [RiskItem(**r) for r in parsed.get("risks", [])]
        high_count = sum(1 for r in risks if r.severity == "HIGH")

        response = RisksResponse(
            session_id=request.session_id,
            risks=risks,
            total_risks=len(risks),
            high_severity_count=high_count,
            generated_at=datetime.now(),
        )

        audit.save_json("parsed_output.json", response.model_dump(), subfolder="step3_agents/agent_risks")
        audit.add_step_completed("risks_identified")

        return response

    def _format_modules(self, modules_output: Dict) -> str:
        """Format modules for prompt."""
        total = modules_output.get("total_modules", 0)
        high_impact = sum(1 for m in modules_output.get("functional_modules", []) + modules_output.get("technical_modules", []) if m.get("impact") == "HIGH")
        return f"{total} modules identified, {high_impact} high-impact"

    def _format_effort(self, effort_output: Dict) -> str:
        """Format effort for prompt."""
        return f"{effort_output.get('total_hours', 0)} hours, {effort_output.get('story_points', 0)} points, {effort_output.get('confidence', 'N/A')} confidence"

    def _format_code(self, code_output: Dict) -> str:
        """Format code impact for prompt."""
        return f"{code_output.get('total_files', 0)} files across {len(code_output.get('repositories_affected', []))} repositories"

    def _parse_response(self, raw: str) -> Dict:
        """Parse LLM JSON response."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ResponseParsingError(f"Failed to parse: {e}", component="risks")
