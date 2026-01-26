import json
from datetime import datetime
from typing import Dict, List, Any
from app.components.base.component import BaseComponent
from app.components.base.exceptions import ResponseParsingError
from app.utils.ollama_client import get_ollama_client
from app.utils.json_repair import parse_llm_json
from app.utils.audit import AuditTrailManager
from app.services.context_assembler import ContextAssembler, ProjectDocuments
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
        """Estimate effort using LLM with filtered context from selected projects."""

        # Format impacted modules summary
        modules_summary = self._format_modules(request.impacted_modules_output)

        # Build filtered estimation context from loaded projects
        if request.loaded_projects:
            # Reconstruct ProjectDocuments from dict for ContextAssembler
            loaded_docs = {}
            for project_id, docs_dict in request.loaded_projects.items():
                try:
                    loaded_docs[project_id] = ProjectDocuments(**docs_dict)
                except Exception as e:
                    # Log and skip invalid project documents
                    audit = AuditTrailManager(request.session_id)
                    audit.save_text(
                        "error.txt",
                        f"Failed to reconstruct ProjectDocuments for {project_id}: {e}",
                        subfolder="step3_agents/agent_estimation_effort"
                    )
                    continue

            # Assemble filtered estimation-specific context
            assembler = ContextAssembler()
            context = await assembler.assemble_agent_context(
                agent_name="estimation_effort",
                loaded_projects=loaded_docs,
                current_requirement=request.requirement_text,
                impacted_modules_output=request.impacted_modules_output,
            )

            # Save the raw estimation sheet data from parser output for audit trail
            audit = AuditTrailManager(request.session_id)
            self._save_estimation_sheet_data(audit, loaded_docs, context)

            # Format the filtered context for LLM prompt
            formatted_context = self._format_estimation_context(context)
        else:
            # Fallback to legacy format if no loaded_projects available
            formatted_context = self._format_matches(request.selected_matches)

        user_prompt = ESTIMATION_EFFORT_USER_PROMPT.format(
            requirement_description=request.requirement_text,
            modules_summary=modules_summary,
            formatted_historical_matches=formatted_context,
        )

        audit = AuditTrailManager(request.session_id)
        audit.save_text("input_prompt.txt", f"{ESTIMATION_EFFORT_SYSTEM_PROMPT}\n\n{user_prompt}", subfolder="step3_agents/agent_estimation_effort")

        raw_response, llm_metadata = await self.ollama.generate(
            system_prompt=ESTIMATION_EFFORT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json",
        )

        # Save LLM request metadata
        audit.save_json("llm_request.json", llm_metadata.to_dict(), subfolder="step3_agents/agent_estimation_effort")
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

    def _save_estimation_sheet_data(
        self,
        audit: AuditTrailManager,
        loaded_docs: Dict[str, ProjectDocuments],
        context: Dict[str, Any],
    ) -> None:
        """Save the raw estimation sheet data from parser output for audit trail.

        Saves two files:
        1. estimation_sheet_raw.json - Full text extraction from each project's estimation Excel
        2. estimation_context.json - Filtered context assembled for the agent

        Args:
            audit: AuditTrailManager instance
            loaded_docs: Dict of project_id → ProjectDocuments with parsed estimation data
            context: Assembled context dict for the estimation effort agent
        """
        subfolder = "step3_agents/agent_estimation_effort"

        # Save raw extraction data (generic full text extraction)
        raw_estimation_data = {}
        for project_id, docs in loaded_docs.items():
            raw_estimation_data[project_id] = {
                "project_id": project_id,
                "tdd_extraction": {
                    "file_name": docs.tdd.file_name,
                    "full_text": docs.tdd.full_text,
                },
                "estimation_extraction": {
                    "file_name": docs.estimation.file_name,
                    "sheet_count": docs.estimation.sheet_count,
                    "full_text": docs.estimation.full_text,
                    "sheets": [s.model_dump() for s in docs.estimation.sheets],
                },
            }

        audit.save_json(
            "estimation_sheet_raw.json",
            raw_estimation_data,
            subfolder=subfolder,
        )

        # Save the assembled context (filtered for estimation effort agent)
        audit.save_json(
            "estimation_context.json",
            context,
            subfolder=subfolder,
        )

    def _format_matches(self, matches: List[Dict]) -> str:
        """Format matches for prompt (legacy fallback)."""
        lines = []
        for m in matches[:3]:
            hours = m.get("actual_hours") or m.get("estimated_hours") or "N/A"
            lines.append(f"- {m.get('epic_name', 'Unknown')}: {hours} hours")
        return "\n".join(lines) if lines else "No historical data."

    def _format_estimation_context(self, context: Dict[str, Any]) -> str:
        """Format estimation context for LLM prompt.

        Uses generic full text extraction. The LLM reasons about the raw
        text content without schema assumptions.

        Args:
            context: Context dict with structure:
                {
                    "current_requirement": str,
                    "similar_projects": [
                        {
                            "project_id": str,
                            "project_name": str,
                            "relevant_data": {
                                "impacted_modules": [...],
                                "tdd_full_text": str,
                                "tdd_file_name": str,
                                "estimation_full_text": str,
                                "estimation_file_name": str,
                                "estimation_sheet_count": int
                            }
                        }
                    ]
                }

        Returns:
            Formatted string for LLM prompt
        """
        lines = []

        for project in context.get("similar_projects", []):
            project_name = project.get("project_name", "Unknown")
            project_id = project.get("project_id", "")
            data = project.get("relevant_data", {})

            lines.append(f"\n## {project_name} ({project_id})")

            # Impacted modules (filtered from analysis)
            impacted_modules = data.get("impacted_modules", [])
            if impacted_modules:
                lines.append(f"\nImpacted Modules ({len(impacted_modules)}):")
                for mod in impacted_modules[:10]:
                    mod_name = mod.get("name", "Unknown")
                    mod_impact = mod.get("impact", "MEDIUM")
                    mod_reason = mod.get("reason", "")[:150]
                    lines.append(f"  - {mod_name} ({mod_impact}): {mod_reason}")

            # Full text extraction from TDD document
            tdd_text = data.get("tdd_full_text", "")
            tdd_file = data.get("tdd_file_name", "TDD.docx")
            if tdd_text:
                lines.append(f"\nTDD Document ({tdd_file}):")
                lines.append("─" * 40)
                lines.append(tdd_text)
                lines.append("─" * 40)

            # Full text extraction from estimation Excel
            estimation_text = data.get("estimation_full_text", "")
            estimation_file = data.get("estimation_file_name", "estimation.xlsx")
            sheet_count = data.get("estimation_sheet_count", 0)

            if estimation_text:
                lines.append(f"\nHistorical Estimation Data ({estimation_file}, {sheet_count} sheets):")
                lines.append("─" * 40)
                lines.append(estimation_text)
                lines.append("─" * 40)

        return "\n".join(lines) if lines else "No estimation data available."

    def _parse_response(self, raw: str) -> Dict:
        """Parse LLM JSON response with automatic repair."""
        try:
            return parse_llm_json(raw, component_name="estimation_effort")
        except json.JSONDecodeError as e:
            raise ResponseParsingError(f"Failed to parse: {e}", component="estimation_effort")
