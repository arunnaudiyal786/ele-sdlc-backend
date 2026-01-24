from typing import Dict, Any, AsyncGenerator, Literal
from datetime import datetime
import json
from pydantic import BaseModel
from app.components.base.component import BaseComponent
from app.utils.audit import AuditTrailManager
from .state import ImpactAssessmentState
from .workflow import create_impact_workflow


# Agent execution order for progress tracking
# NOTE: Only include agents that are actually enabled in the workflow
# Disabled agents (code_impact, risks) should NOT be in this list
AGENT_ORDER = [
    "requirement",
    "historical_match",
    "auto_select",
    "impacted_modules",
    "estimation_effort",
    "tdd",
    "jira_stories",
]


class StreamEventData(BaseModel):
    """Data payload for streaming events."""
    agent_name: str | None = None
    agent_index: int | None = None
    total_agents: int = len(AGENT_ORDER)
    status: str | None = None
    output: Dict | None = None
    error: str | None = None
    progress_percent: int | None = None


class StreamEvent(BaseModel):
    """SSE event structure for pipeline streaming."""
    type: Literal["pipeline_start", "agent_complete", "pipeline_complete", "pipeline_error"]
    session_id: str
    timestamp: str
    data: StreamEventData


class PipelineRequest(BaseModel):
    """Request to run full pipeline."""
    session_id: str
    requirement_text: str
    jira_epic_id: str | None = None
    selected_matches: list[Dict] = []


class PipelineResponse(BaseModel):
    """Response with full impact assessment."""
    session_id: str
    status: str
    historical_matches: list[Dict] = []
    requirement_text: str | None = None
    extracted_keywords: list[str] = []
    impacted_modules_output: Dict | None = None
    estimation_effort_output: Dict | None = None
    tdd_output: Dict | None = None
    jira_stories_output: Dict | None = None
    code_impact_output: Dict | None = None
    risks_output: Dict | None = None
    messages: list[Dict] = []
    error_message: str | None = None


class OrchestratorService(BaseComponent[PipelineRequest, PipelineResponse]):
    """Orchestrator service for full pipeline execution."""

    def __init__(self):
        self.workflow = create_impact_workflow()

    @property
    def component_name(self) -> str:
        return "orchestrator"

    async def process(self, request: PipelineRequest) -> PipelineResponse:
        """Run full impact assessment pipeline."""
        initial_state: ImpactAssessmentState = {
            "session_id": request.session_id,
            "requirement_text": request.requirement_text,
            "jira_epic_id": request.jira_epic_id,
            "selected_matches": request.selected_matches,
            "status": "created",
            "current_agent": "requirement",
            "messages": [],
        }

        # Run workflow
        final_state = await self.workflow.ainvoke(initial_state)

        # Save final summary
        audit = AuditTrailManager(request.session_id)
        audit.save_json("final_summary.json", {
            "session_id": request.session_id,
            "status": final_state.get("status"),
            "completed_at": datetime.now().isoformat(),
            "impacted_modules": final_state.get("impacted_modules_output"),
            "estimation_effort": final_state.get("estimation_effort_output"),
            "tdd": final_state.get("tdd_output"),
            "jira_stories": final_state.get("jira_stories_output"),
            "code_impact": final_state.get("code_impact_output"),
            "risks": final_state.get("risks_output"),
        })

        # Load historical matches and requirement data for response
        all_matches = audit.load_json("step2_historical_match/all_matches.json")
        requirement_data = audit.load_json("step1_input/requirement.json")

        return PipelineResponse(
            session_id=request.session_id,
            status=final_state.get("status", "unknown"),
            historical_matches=all_matches if isinstance(all_matches, list) else [],
            requirement_text=requirement_data.get("requirement_text") if requirement_data else request.requirement_text,
            extracted_keywords=requirement_data.get("extracted_keywords", []) if requirement_data else [],
            impacted_modules_output=final_state.get("impacted_modules_output"),
            estimation_effort_output=final_state.get("estimation_effort_output"),
            tdd_output=final_state.get("tdd_output"),
            jira_stories_output=final_state.get("jira_stories_output"),
            code_impact_output=final_state.get("code_impact_output"),
            risks_output=final_state.get("risks_output"),
            messages=final_state.get("messages", []),
            error_message=final_state.get("error_message"),
        )

    async def get_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary for a completed session including historical matches."""
        audit = AuditTrailManager(session_id)
        raw_summary = audit.load_json("final_summary.json")

        if not raw_summary:
            raw_summary = {}

        # Map keys to frontend expected format (with _output suffix)
        summary: Dict[str, Any] = {
            "session_id": raw_summary.get("session_id", session_id),
            "status": raw_summary.get("status", "unknown"),
            "impacted_modules_output": raw_summary.get("impacted_modules") or raw_summary.get("impacted_modules_output"),
            "estimation_effort_output": raw_summary.get("estimation_effort") or raw_summary.get("estimation_effort_output"),
            "tdd_output": raw_summary.get("tdd") or raw_summary.get("tdd_output"),
            "jira_stories_output": raw_summary.get("jira_stories") or raw_summary.get("jira_stories_output"),
            "code_impact_output": raw_summary.get("code_impact") or raw_summary.get("code_impact_output"),
            "risks_output": raw_summary.get("risks") or raw_summary.get("risks_output"),
            "messages": raw_summary.get("messages", []),
            "error_message": raw_summary.get("error_message"),
        }

        # Load historical matches from step2 if available
        all_matches = audit.load_json("step2_historical_match/all_matches.json")
        if all_matches:
            summary["historical_matches"] = all_matches

        # Load requirement input for context
        requirement = audit.load_json("step1_input/requirement.json")
        if requirement:
            summary["requirement_text"] = requirement.get("requirement_text")
            summary["extracted_keywords"] = requirement.get("extracted_keywords", [])

        return summary

    def _format_sse_event(self, event: StreamEvent) -> str:
        """Format event as SSE string."""
        return f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"

    async def process_streaming(self, request: PipelineRequest) -> AsyncGenerator[str, None]:
        """Run pipeline with streaming progress updates via SSE."""
        initial_state: ImpactAssessmentState = {
            "session_id": request.session_id,
            "requirement_text": request.requirement_text,
            "jira_epic_id": request.jira_epic_id,
            "selected_matches": request.selected_matches,
            "status": "created",
            "current_agent": "requirement",
            "messages": [],
        }

        # Emit pipeline_start event
        yield self._format_sse_event(StreamEvent(
            type="pipeline_start",
            session_id=request.session_id,
            timestamp=datetime.now().isoformat(),
            data=StreamEventData(progress_percent=0)
        ))

        final_state = initial_state.copy()

        try:
            # Stream updates from LangGraph workflow
            async for chunk in self.workflow.astream(initial_state, stream_mode="updates"):
                for node_name, node_output in chunk.items():
                    # Skip internal nodes like __start__, __end__
                    if node_name.startswith("__"):
                        continue

                    # Update accumulated state
                    final_state.update(node_output)

                    # Calculate progress
                    agent_idx = AGENT_ORDER.index(node_name) if node_name in AGENT_ORDER else -1
                    progress = int(((agent_idx + 1) / len(AGENT_ORDER)) * 100) if agent_idx >= 0 else 0

                    # Check for errors
                    if node_output.get("status") == "error":
                        yield self._format_sse_event(StreamEvent(
                            type="pipeline_error",
                            session_id=request.session_id,
                            timestamp=datetime.now().isoformat(),
                            data=StreamEventData(
                                agent_name=node_name,
                                agent_index=agent_idx,
                                status="error",
                                error=node_output.get("error_message", "Unknown error"),
                                progress_percent=progress
                            )
                        ))
                        return

                    # Emit agent_complete event
                    yield self._format_sse_event(StreamEvent(
                        type="agent_complete",
                        session_id=request.session_id,
                        timestamp=datetime.now().isoformat(),
                        data=StreamEventData(
                            agent_name=node_name,
                            agent_index=agent_idx,
                            status=node_output.get("status"),
                            output=node_output,
                            progress_percent=progress
                        )
                    ))

            # Save final summary
            audit = AuditTrailManager(request.session_id)
            audit.save_json("final_summary.json", {
                "session_id": request.session_id,
                "status": final_state.get("status"),
                "completed_at": datetime.now().isoformat(),
                "impacted_modules": final_state.get("impacted_modules_output"),
                "estimation_effort": final_state.get("estimation_effort_output"),
                "tdd": final_state.get("tdd_output"),
                "jira_stories": final_state.get("jira_stories_output"),
                "code_impact": final_state.get("code_impact_output"),
                "risks": final_state.get("risks_output"),
            })

            # Load historical matches for final output
            all_matches = audit.load_json("step2_historical_match/all_matches.json")
            requirement_data = audit.load_json("step1_input/requirement.json")

            # Emit pipeline_complete event with final outputs
            # IMPORTANT: Always send status="completed" for pipeline_complete event
            # The frontend wizard depends on this to transition to results page
            yield self._format_sse_event(StreamEvent(
                type="pipeline_complete",
                session_id=request.session_id,
                timestamp=datetime.now().isoformat(),
                data=StreamEventData(
                    status="completed",
                    progress_percent=100,
                    output={
                        "historical_matches": all_matches if all_matches else [],
                        "requirement_text": requirement_data.get("requirement_text") if requirement_data else None,
                        "impacted_modules_output": final_state.get("impacted_modules_output"),
                        "estimation_effort_output": final_state.get("estimation_effort_output"),
                        "tdd_output": final_state.get("tdd_output"),
                        "jira_stories_output": final_state.get("jira_stories_output"),
                        "code_impact_output": final_state.get("code_impact_output"),
                        "risks_output": final_state.get("risks_output"),
                        "messages": final_state.get("messages", []),
                    }
                )
            ))

        except Exception as e:
            yield self._format_sse_event(StreamEvent(
                type="pipeline_error",
                session_id=request.session_id,
                timestamp=datetime.now().isoformat(),
                data=StreamEventData(
                    status="error",
                    error=str(e)
                )
            ))
