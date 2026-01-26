import json
from datetime import datetime
from typing import Dict
from app.components.base.component import BaseComponent
from app.components.base.exceptions import ResponseParsingError
from app.utils.ollama_client import get_ollama_client
from app.utils.json_repair import parse_llm_json
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
        # Extract historical TDDs from selected project(s)
        historical_tdds = self._format_historical_tdds(request.loaded_projects)

        user_prompt = TDD_USER_PROMPT.format(
            requirement_description=request.requirement_text,
            historical_tdds=historical_tdds,
        )

        audit = AuditTrailManager(request.session_id)
        audit.save_text("input_prompt.txt", f"{TDD_SYSTEM_PROMPT}\n\n{user_prompt}", subfolder="step3_agents/agent_tdd")

        raw_response, llm_metadata = await self.ollama.generate(
            system_prompt=TDD_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json",
        )

        # Save LLM request metadata
        audit.save_json("llm_request.json", llm_metadata.to_dict(), subfolder="step3_agents/agent_tdd")
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

    def _format_historical_tdds(self, loaded_projects: Dict) -> str:
        """Extract and format historical TDDs from loaded project documents.

        Uses full_text extraction from TDD documents to provide complete
        reference content for generating new TDDs.

        Args:
            loaded_projects: Dict mapping project_id -> ProjectDocuments (as dict)

        Returns:
            Formatted string of historical TDD content for use in prompt
        """
        if not loaded_projects:
            return "No reference TDDs available."

        all_tdds = []

        for project_id, project_data in loaded_projects.items():
            # Extract TDD from project data
            tdd_data = project_data.get("tdd", {})

            if not tdd_data:
                continue

            # Get full text - this is the complete TDD document content
            full_text = tdd_data.get("full_text", "")
            file_name = tdd_data.get("file_name", "TDD.docx")

            if not full_text:
                continue

            all_tdds.append(f"\n{'='*60}")
            all_tdds.append(f"PROJECT: {project_id}")
            all_tdds.append(f"TDD Document: {file_name}")
            all_tdds.append(f"{'='*60}")
            all_tdds.append(full_text)

        if not all_tdds:
            return "No reference TDDs available."

        return "\n".join(all_tdds)

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
        """Parse LLM JSON response with automatic repair."""
        try:
            return parse_llm_json(raw, component_name="tdd")
        except json.JSONDecodeError as e:
            raise ResponseParsingError(f"Failed to parse: {e}", component="tdd")
