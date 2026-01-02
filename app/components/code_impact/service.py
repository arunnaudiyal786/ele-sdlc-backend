import json
from datetime import datetime
from typing import Dict, List
from app.components.base.component import BaseComponent
from app.components.base.exceptions import ResponseParsingError
from app.utils.ollama_client import get_ollama_client
from app.utils.audit import AuditTrailManager
from .models import CodeImpactRequest, CodeImpactResponse, CodeFile
from .prompts import CODE_IMPACT_SYSTEM_PROMPT, CODE_IMPACT_USER_PROMPT


class CodeImpactService(BaseComponent[CodeImpactRequest, CodeImpactResponse]):
    """Code impact analysis agent as a component."""

    def __init__(self):
        self.ollama = get_ollama_client()

    @property
    def component_name(self) -> str:
        return "code_impact"

    async def process(self, request: CodeImpactRequest) -> CodeImpactResponse:
        """Analyze code impact using LLM."""
        modules_summary = self._format_modules(request.modules_output)
        stories_summary = self._format_stories(request.stories_output)

        user_prompt = CODE_IMPACT_USER_PROMPT.format(
            requirement_description=request.requirement_text,
            modules_summary=modules_summary,
            stories_summary=stories_summary,
        )

        audit = AuditTrailManager(request.session_id)
        audit.save_text("input_prompt.txt", f"{CODE_IMPACT_SYSTEM_PROMPT}\n\n{user_prompt}", subfolder="step3_agents/agent_code")

        raw_response = await self.ollama.generate(
            system_prompt=CODE_IMPACT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json",
        )

        audit.save_text("raw_response.txt", raw_response, subfolder="step3_agents/agent_code")

        parsed = self._parse_response(raw_response)
        files = [CodeFile(**f) for f in parsed.get("files", [])]
        repos = list(set(f.repository for f in files))

        response = CodeImpactResponse(
            session_id=request.session_id,
            files=files,
            total_files=len(files),
            repositories_affected=repos,
            generated_at=datetime.now(),
        )

        audit.save_json("parsed_output.json", response.model_dump(), subfolder="step3_agents/agent_code")
        audit.add_step_completed("code_impact_analyzed")

        return response

    def _format_modules(self, modules_output: Dict) -> str:
        """Format modules for prompt."""
        lines = []
        for m in modules_output.get("functional_modules", []):
            lines.append(f"- {m.get('name')}")
        for m in modules_output.get("technical_modules", []):
            lines.append(f"- {m.get('name')}")
        return "\n".join(lines) if lines else "No modules."

    def _format_stories(self, stories_output: Dict) -> str:
        """Format stories for prompt."""
        lines = []
        for s in stories_output.get("stories", [])[:5]:
            lines.append(f"- {s.get('title')}")
        return "\n".join(lines) if lines else "No stories."

    def _parse_response(self, raw: str) -> Dict:
        """Parse LLM JSON response."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ResponseParsingError(f"Failed to parse: {e}", component="code_impact")
