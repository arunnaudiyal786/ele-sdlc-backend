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

    def _format_matches(self, matches: List[Dict]) -> str:
        """Format matches for prompt (legacy fallback)."""
        lines = []
        for m in matches[:3]:
            hours = m.get("actual_hours") or m.get("estimated_hours") or "N/A"
            lines.append(f"- {m.get('epic_name', 'Unknown')}: {hours} hours")
        return "\n".join(lines) if lines else "No historical data."

    def _format_estimation_context(self, context: Dict[str, Any]) -> str:
        """Format filtered estimation context for LLM prompt.

        This method formats the context assembled by ContextAssembler, which includes:
        - Only impacted modules (not full TDD module_list)
        - Only estimation data from selected historical matches

        Args:
            context: Context dict with structure:
                {
                    "current_requirement": str,
                    "similar_projects": [
                        {
                            "project_id": str,
                            "project_name": str,
                            "relevant_data": {
                                "epic_description": str,
                                "impacted_modules": [...],  # Filtered modules only
                                "total_dev_points": float,
                                "total_qa_points": float,
                                "task_breakdown": [...],
                                "assumptions_and_risks": [...]
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

            # Epic description for context
            epic_desc = data.get("epic_description", "")
            if epic_desc:
                lines.append(f"Epic: {epic_desc[:200]}")

            # Impacted modules (filtered from analysis, not full TDD module_list)
            impacted_modules = data.get("impacted_modules", [])
            if impacted_modules:
                lines.append(f"\nImpacted Modules ({len(impacted_modules)}):")
                for mod in impacted_modules[:10]:  # Limit to 10 most relevant
                    mod_name = mod.get("name", "Unknown")
                    mod_impact = mod.get("impact", "MEDIUM")
                    mod_reason = mod.get("reason", "")[:150]  # Truncate long reasons
                    lines.append(f"  - {mod_name} ({mod_impact}): {mod_reason}")

            # Historical estimation data
            total_dev = data.get("total_dev_points", 0)
            total_qa = data.get("total_qa_points", 0)
            lines.append(f"\nHistorical Effort:")
            lines.append(f"  - Dev Points: {total_dev}")
            lines.append(f"  - QA Points: {total_qa}")
            lines.append(f"  - Total: {total_dev + total_qa}")

            # Task breakdown (show top 5 tasks as examples)
            task_breakdown = data.get("task_breakdown", [])
            if task_breakdown:
                lines.append(f"\nKey Tasks (showing {min(5, len(task_breakdown))} of {len(task_breakdown)}):")
                for task in task_breakdown[:5]:
                    desc = task.get("task_description", "")[:100]  # Truncate long descriptions
                    dev = task.get("dev_points", 0)
                    qa = task.get("qa_points", 0)
                    lines.append(f"  - {desc} (Dev: {dev}, QA: {qa})")

            # Assumptions and risks (if available)
            assumptions = data.get("assumptions_and_risks", [])
            if assumptions:
                lines.append(f"\nKey Assumptions/Risks (showing {min(3, len(assumptions))}):")
                for assumption in assumptions[:3]:
                    lines.append(f"  - {assumption[:150]}")  # Truncate long assumptions

        return "\n".join(lines) if lines else "No estimation data available."

    def _parse_response(self, raw: str) -> Dict:
        """Parse LLM JSON response with automatic repair."""
        try:
            return parse_llm_json(raw, component_name="estimation_effort")
        except json.JSONDecodeError as e:
            raise ResponseParsingError(f"Failed to parse: {e}", component="estimation_effort")
