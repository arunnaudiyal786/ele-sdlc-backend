from typing import Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.components.base.component import BaseComponent
from app.utils.audit import AuditTrailManager
from .state import ImpactAssessmentState
from .workflow import create_impact_workflow


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

        return PipelineResponse(
            session_id=request.session_id,
            status=final_state.get("status", "unknown"),
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
        """Get summary for a completed session."""
        audit = AuditTrailManager(session_id)
        return audit.load_json("final_summary.json")
