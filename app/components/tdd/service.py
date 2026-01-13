import json
from datetime import datetime
from typing import Dict, List
from app.components.base.component import BaseComponent
from app.components.base.exceptions import ResponseParsingError
from app.utils.ollama_client import get_ollama_client
from app.utils.audit import AuditTrailManager
from .models import TDDRequest, TDDResponse
from .prompts import TDD_SYSTEM_PROMPT, TDD_USER_PROMPT, TDD_MARKDOWN_TEMPLATE


class TDDService(BaseComponent[TDDRequest, TDDResponse]):
    """TDD generation agent as a component."""

    def __init__(self):
        self.ollama = get_ollama_client()

    @property
    def component_name(self) -> str:
        return "tdd"

    async def process(self, request: TDDRequest) -> TDDResponse:
        """Generate TDD document using LLM."""
        modules_summary = self._format_modules(request.impacted_modules_output)
        effort_summary = self._format_effort(request.estimation_effort_output)
        historical_matches = self._format_matches(request.selected_matches)

        user_prompt = TDD_USER_PROMPT.format(
            requirement_description=request.requirement_text,
            modules_summary=modules_summary,
            effort_summary=effort_summary,
            historical_matches=historical_matches,
        )

        audit = AuditTrailManager(request.session_id)
        audit.save_text("input_prompt.txt", f"{TDD_SYSTEM_PROMPT}\n\n{user_prompt}", subfolder="step3_agents/agent_tdd")

        raw_response = await self.ollama.generate(
            system_prompt=TDD_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json",
        )

        audit.save_text("raw_response.txt", raw_response, subfolder="step3_agents/agent_tdd")

        parsed = self._parse_response(raw_response)
        generated_at = datetime.now()

        # Generate markdown content
        markdown_content = self._generate_markdown(
            parsed=parsed,
            modules_output=request.impacted_modules_output,
            effort_output=request.estimation_effort_output,
            session_id=request.session_id,
            generated_at=generated_at,
        )

        # Save markdown file
        markdown_file_path = str(audit.save_text("tdd.md", markdown_content, subfolder="step3_agents/agent_tdd"))

        response = TDDResponse(
            session_id=request.session_id,
            tdd_name=parsed.get("tdd_name", "Technical Design Document"),
            tdd_description=parsed.get("tdd_description", ""),
            technical_components=parsed.get("technical_components", []),
            design_decisions=parsed.get("design_decisions", ""),
            architecture_pattern=parsed.get("architecture_pattern", ""),
            security_considerations=parsed.get("security_considerations", ""),
            performance_requirements=parsed.get("performance_requirements", ""),
            tdd_dependencies=parsed.get("tdd_dependencies", []),
            markdown_content=markdown_content,
            markdown_file_path=markdown_file_path,
            generated_at=generated_at,
        )

        audit.save_json("parsed_output.json", response.model_dump(), subfolder="step3_agents/agent_tdd")
        audit.add_step_completed("tdd_generated")

        return response

    def _format_modules(self, modules_output: Dict) -> str:
        """Format modules for prompt."""
        lines = []
        for m in modules_output.get("functional_modules", [])[:5]:
            lines.append(f"- {m.get('name')} ({m.get('impact')}): {m.get('reason', '')[:100]}")
        for m in modules_output.get("technical_modules", [])[:5]:
            lines.append(f"- {m.get('name')} ({m.get('impact')}): {m.get('reason', '')[:100]}")
        return "\n".join(lines) if lines else "No modules identified."

    def _format_effort(self, effort_output: Dict) -> str:
        """Format effort for prompt."""
        return (
            f"Dev Hours: {effort_output.get('total_dev_hours', 0)}, "
            f"QA Hours: {effort_output.get('total_qa_hours', 0)}, "
            f"Story Points: {effort_output.get('story_points', 0)}, "
            f"Confidence: {effort_output.get('confidence', 'N/A')}"
        )

    def _format_matches(self, matches: List[Dict]) -> str:
        """Format historical matches for prompt."""
        lines = []
        for m in matches[:3]:
            lines.append(f"- {m.get('epic_name', 'Unknown')}: {m.get('description', '')[:150]}")
        return "\n".join(lines) if lines else "No historical matches."

    def _generate_markdown(
        self,
        parsed: Dict,
        modules_output: Dict,
        effort_output: Dict,
        session_id: str,
        generated_at: datetime,
    ) -> str:
        """Generate markdown content from parsed TDD."""
        # Format technical components as list
        tech_components = parsed.get("technical_components", [])
        tech_list = "\n".join([f"- {c}" for c in tech_components]) if tech_components else "- None specified"

        # Format dependencies as list
        dependencies = parsed.get("tdd_dependencies", [])
        deps_list = "\n".join([f"- {d}" for d in dependencies]) if dependencies else "- None specified"

        # Format functional modules
        func_modules = modules_output.get("functional_modules", [])
        func_list = "\n".join([f"- **{m.get('name')}** ({m.get('impact')}): {m.get('reason', 'N/A')}" for m in func_modules]) if func_modules else "- None identified"

        # Format technical modules
        tech_modules = modules_output.get("technical_modules", [])
        tech_mod_list = "\n".join([f"- **{m.get('name')}** ({m.get('impact')}): {m.get('reason', 'N/A')}" for m in tech_modules]) if tech_modules else "- None identified"

        return TDD_MARKDOWN_TEMPLATE.format(
            tdd_name=parsed.get("tdd_name", "Technical Design Document"),
            tdd_description=parsed.get("tdd_description", "No description provided."),
            architecture_pattern=parsed.get("architecture_pattern", "Not specified"),
            technical_components_list=tech_list,
            design_decisions=parsed.get("design_decisions", "No design decisions documented."),
            dependencies_list=deps_list,
            security_considerations=parsed.get("security_considerations", "No security considerations documented."),
            performance_requirements=parsed.get("performance_requirements", "No performance requirements documented."),
            functional_modules_list=func_list,
            technical_modules_list=tech_mod_list,
            dev_hours=effort_output.get("total_dev_hours", 0),
            qa_hours=effort_output.get("total_qa_hours", 0),
            total_hours=effort_output.get("total_hours", 0),
            story_points=effort_output.get("story_points", 0),
            confidence=effort_output.get("confidence", "N/A"),
            generated_at=generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            session_id=session_id,
        )

    def _parse_response(self, raw: str) -> Dict:
        """Parse LLM JSON response."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ResponseParsingError(f"Failed to parse: {e}", component="tdd")
