import json
from datetime import datetime
from typing import Dict, List
from app.components.base.component import BaseComponent
from app.components.base.exceptions import ResponseParsingError
from app.utils.ollama_client import get_ollama_client
from app.utils.audit import AuditTrailManager
from .models import ModulesRequest, ModulesResponse, ModuleItem
from .prompts import MODULES_SYSTEM_PROMPT, MODULES_USER_PROMPT


class ModulesService(BaseComponent[ModulesRequest, ModulesResponse]):
    """Modules identification agent as a component."""

    def __init__(self):
        self.ollama = get_ollama_client()

    @property
    def component_name(self) -> str:
        return "modules"

    async def process(self, request: ModulesRequest) -> ModulesResponse:
        """Identify impacted modules using LLM."""
        formatted_matches = self._format_matches(request.selected_matches)
        user_prompt = MODULES_USER_PROMPT.format(
            requirement_description=request.requirement_text,
            formatted_historical_matches=formatted_matches,
        )

        # Save input prompt
        audit = AuditTrailManager(request.session_id)
        audit.save_text("input_prompt.txt", f"{MODULES_SYSTEM_PROMPT}\n\n{user_prompt}", subfolder="step3_agents/agent_modules")

        raw_response = await self.ollama.generate(
            system_prompt=MODULES_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json",
        )

        audit.save_text("raw_response.txt", raw_response, subfolder="step3_agents/agent_modules")

        parsed = self._parse_response(raw_response)
        functional = [ModuleItem(**m) for m in parsed.get("functional_modules", [])]
        technical = [ModuleItem(**m) for m in parsed.get("technical_modules", [])]

        response = ModulesResponse(
            session_id=request.session_id,
            functional_modules=functional,
            technical_modules=technical,
            total_modules=len(functional) + len(technical),
            generated_at=datetime.now(),
        )

        audit.save_json("parsed_output.json", response.model_dump(), subfolder="step3_agents/agent_modules")
        audit.add_step_completed("modules_generated")

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
                component="modules",
                details={"raw_response": raw[:500]},
            )
