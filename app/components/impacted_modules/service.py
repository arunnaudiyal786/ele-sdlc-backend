import json
from datetime import datetime
from typing import Dict, List
from app.components.base.component import BaseComponent
from app.components.base.exceptions import ResponseParsingError
from app.utils.ollama_client import get_ollama_client
from app.utils.audit import AuditTrailManager
from .models import ImpactedModulesRequest, ImpactedModulesResponse, ModuleItem
from .prompts import IMPACTED_MODULES_SYSTEM_PROMPT, IMPACTED_MODULES_USER_PROMPT


class ImpactedModulesService(BaseComponent[ImpactedModulesRequest, ImpactedModulesResponse]):
    """Impacted modules identification agent as a component."""

    def __init__(self):
        self.ollama = get_ollama_client()

    @property
    def component_name(self) -> str:
        return "impacted_modules"

    async def process(self, request: ImpactedModulesRequest) -> ImpactedModulesResponse:
        """Identify impacted modules using LLM."""
        formatted_matches = self._format_matches(request.selected_matches)
        user_prompt = IMPACTED_MODULES_USER_PROMPT.format(
            requirement_description=request.requirement_text,
            formatted_historical_matches=formatted_matches,
        )

        # Save input prompt
        audit = AuditTrailManager(request.session_id)
        audit.save_text("input_prompt.txt", f"{IMPACTED_MODULES_SYSTEM_PROMPT}\n\n{user_prompt}", subfolder="step3_agents/agent_impacted_modules")

        raw_response = await self.ollama.generate(
            system_prompt=IMPACTED_MODULES_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json",
        )

        audit.save_text("raw_response.txt", raw_response, subfolder="step3_agents/agent_impacted_modules")

        parsed = self._parse_response(raw_response)
        functional = [ModuleItem(**m) for m in parsed.get("functional_modules", [])]
        technical = [ModuleItem(**m) for m in parsed.get("technical_modules", [])]

        response = ImpactedModulesResponse(
            session_id=request.session_id,
            functional_modules=functional,
            technical_modules=technical,
            total_modules=len(functional) + len(technical),
            generated_at=datetime.now(),
        )

        audit.save_json("parsed_output.json", response.model_dump(), subfolder="step3_agents/agent_impacted_modules")
        audit.add_step_completed("impacted_modules_generated")

        return response

    def _format_matches(self, matches: List[Dict]) -> str:
        """Format matches for prompt."""
        lines = []
        for i, m in enumerate(matches[:5], 1):
            lines.append(f"{i}. {m.get('epic_name', 'Unknown')}: {m.get('description', '')[:200]}")
        return "\n".join(lines) if lines else "No historical matches available."

    def _parse_response(self, raw: str) -> Dict:
        """Parse LLM JSON response."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ResponseParsingError(
                f"Failed to parse LLM response: {e}",
                component="impacted_modules",
                details={"raw_response": raw[:500]},
            )
