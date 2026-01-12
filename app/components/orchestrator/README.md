# Orchestrator Component

The **orchestrator** component is the central nervous system of the impact assessment pipeline. It uses **LangGraph** to define and execute a multi-agent workflow, coordinating the flow between requirement processing, search, and all AI analysis agents.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR COMPONENT                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌────────────────────┐                   │
│  │   Router     │─────▶│OrchestratorService │                   │
│  │  (FastAPI)   │      │  (BaseComponent)   │                   │
│  └──────────────┘      └─────────┬──────────┘                   │
│                                  │                               │
│                                  │ uses                          │
│                                  ▼                               │
│               ┌──────────────────────────────────┐              │
│               │      LangGraph Workflow           │              │
│               │      (StateGraph)                 │              │
│               └────────────────┬─────────────────┘              │
│                                │                                 │
│     ┌──────────────────────────┼──────────────────────────┐     │
│     │                          │                          │     │
│     ▼                          ▼                          ▼     │
│  ┌────────┐  ┌────────┐  ┌──────────┐  ┌────────┐  ┌────────┐  │
│  │require-│─▶│ search │─▶│auto_sel- │─▶│modules │─▶│ effort │  │
│  │  ment  │  │        │  │   ect    │  │        │  │        │  │
│  └────────┘  └────────┘  └──────────┘  └────────┘  └───┬────┘  │
│                                                         │       │
│  ┌────────┐  ┌────────┐  ┌──────────┐                   │       │
│  │  END   │◀─│ risks  │◀─│code_imp- │◀─┬──────┐         │       │
│  │        │  │        │  │   act    │  │stories│◀────────┘       │
│  └────────┘  └────────┘  └──────────┘  └──────┘                 │
│                                                                  │
│  ┌─────────────────────┐                                        │
│  │ ImpactAssessmentState│  TypedDict for workflow state         │
│  │     (state.py)       │                                       │
│  └─────────────────────┘                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
orchestrator/
├── __init__.py      # Public exports
├── state.py         # TypedDict workflow state definition
├── workflow.py      # LangGraph graph construction and routing
├── service.py       # Pipeline execution and result aggregation
├── router.py        # FastAPI endpoints
└── README.md        # This file
```

## LangGraph Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORKFLOW GRAPH                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                        ┌───────────┐                            │
│                        │   START   │                            │
│                        └─────┬─────┘                            │
│                              │                                   │
│                              ▼                                   │
│                     ┌─────────────────┐                         │
│                     │   requirement   │  Extract keywords        │
│                     └────────┬────────┘                         │
│                              │                                   │
│                              ▼                                   │
│                     ┌─────────────────┐                         │
│                     │     search      │  Find similar projects  │
│                     └────────┬────────┘                         │
│                              │                                   │
│                 ┌────────────┴────────────┐                     │
│                 │   route_after_search    │                     │
│                 └────────────┬────────────┘                     │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│         ┌─────────┐   ┌───────────┐   ┌───────────┐            │
│         │  error  │   │auto_select│   │   END     │            │
│         │ handler │   │           │   │(no match) │            │
│         └────┬────┘   └─────┬─────┘   └───────────┘            │
│              │              │                                    │
│              │              ▼                                    │
│              │      ┌─────────────────┐                         │
│              │      │    modules      │  Identify modules       │
│              │      └────────┬────────┘                         │
│              │              │                                    │
│              │              ▼                                    │
│              │      ┌─────────────────┐                         │
│              │      │     effort      │  Estimate hours         │
│              │      └────────┬────────┘                         │
│              │              │                                    │
│              │              ▼                                    │
│              │      ┌─────────────────┐                         │
│              │      │    stories      │  Generate Jira stories  │
│              │      └────────┬────────┘                         │
│              │              │                                    │
│              │              ▼                                    │
│              │      ┌─────────────────┐                         │
│              │      │  code_impact    │  Analyze code changes   │
│              │      └────────┬────────┘                         │
│              │              │                                    │
│              │              ▼                                    │
│              │      ┌─────────────────┐                         │
│              │      │     risks       │  Identify risks         │
│              │      └────────┬────────┘                         │
│              │              │                                    │
│              └──────────────┼──────────────────────────────────│
│                             │                                    │
│                             ▼                                    │
│                        ┌─────────┐                              │
│                        │   END   │                              │
│                        └─────────┘                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Code Walkthrough

### 1. State (`state.py`)

Defines the TypedDict that flows through the entire workflow.

```python
from typing import TypedDict, Annotated, List, Dict, Optional, Literal
import operator

class ImpactAssessmentState(TypedDict, total=False):
    """Workflow state for impact assessment pipeline.

    Using total=False allows nodes to return PARTIAL updates.
    LangGraph automatically merges partial returns into full state.
    """

    # SESSION CONTEXT - Set at workflow start
    session_id: str
    requirement_text: str
    jira_epic_id: Optional[str]
    extracted_keywords: List[str]

    # SEARCH RESULTS - Set by search component
    all_matches: List[Dict]
    selected_matches: List[Dict]

    # AGENT OUTPUTS - Set by each agent component
    modules_output: Dict
    effort_output: Dict
    stories_output: Dict
    code_impact_output: Dict
    risks_output: Dict

    # CONTROL FIELDS - Updated throughout workflow
    status: Literal[
        "created",
        "requirement_submitted",
        "matches_found",
        "matches_selected",
        "generating_impact",
        "completed",
        "error",
    ]
    current_agent: str
    error_message: Optional[str]

    # TIMING & AUDIT
    timing: Dict[str, int]

    # Accumulated messages (uses operator.add reducer)
    messages: Annotated[List[Dict], operator.add]
```

**Key Design Decision - `total=False`:**

This allows agent nodes to return only the fields they modify, not the entire state:

```python
# Node can return just what changed:
return {
    "modules_output": {...},
    "status": "modules_generated",
    "current_agent": "effort"
}
# Instead of returning the entire state dict
```

**Message Accumulation with `Annotated`:**

```python
messages: Annotated[List[Dict], operator.add]
```

This tells LangGraph to **append** new messages rather than replace:

```python
# State before: messages = [{"role": "requirement", ...}]
# Node returns: messages = [{"role": "search", ...}]
# State after:  messages = [{"role": "requirement", ...}, {"role": "search", ...}]
```

---

### 2. Workflow (`workflow.py`)

Constructs the LangGraph state machine.

```python
from langgraph.graph import StateGraph, END
from .state import ImpactAssessmentState

def create_impact_workflow() -> StateGraph:
    """Create the LangGraph workflow for impact assessment."""
    workflow = StateGraph(ImpactAssessmentState)

    # Add all nodes
    workflow.add_node("requirement", requirement_agent)
    workflow.add_node("search", search_agent)
    workflow.add_node("auto_select", auto_select_node)
    workflow.add_node("modules", modules_agent)
    workflow.add_node("effort", effort_agent)
    workflow.add_node("stories", stories_agent)
    workflow.add_node("code_impact", code_impact_agent)
    workflow.add_node("risks", risks_agent)
    workflow.add_node("error_handler", error_handler_node)

    # Set entry point
    workflow.set_entry_point("requirement")

    # Wire edges
    workflow.add_edge("requirement", "search")
    workflow.add_conditional_edges(
        "search",
        route_after_search,
        {"auto_select": "auto_select", "error_handler": "error_handler"},
    )
    workflow.add_conditional_edges(
        "auto_select",
        route_after_auto_select,
        {"modules": "modules", "error_handler": "error_handler", END: END},
    )
    workflow.add_edge("modules", "effort")
    workflow.add_edge("effort", "stories")
    workflow.add_edge("stories", "code_impact")
    workflow.add_edge("code_impact", "risks")
    workflow.add_edge("risks", END)
    workflow.add_edge("error_handler", END)

    return workflow.compile()
```

**Auto-Select Node (File-Based Pipeline Support):**

```python
async def auto_select_node(state: ImpactAssessmentState) -> dict:
    """Auto-select top matches if none are pre-selected.

    This enables file-based pipeline execution without manual selection.
    """
    # If matches are already selected, pass through
    if state.get("selected_matches"):
        return {
            "status": "matches_selected",
            "current_agent": "modules",
            "messages": [{
                "role": "auto_select",
                "content": f"Using {len(state['selected_matches'])} pre-selected matches",
            }],
        }

    # Auto-select top 5 matches
    all_matches = state.get("all_matches", [])
    if not all_matches:
        return {
            "status": "error",
            "error_message": "No matches found for auto-selection",
            "current_agent": "error_handler",
        }

    sorted_matches = sorted(
        all_matches,
        key=lambda m: m.get("score", 0),
        reverse=True
    )
    top_matches = sorted_matches[:5]

    return {
        "selected_matches": top_matches,
        "status": "matches_selected",
        "current_agent": "modules",
        "messages": [{
            "role": "auto_select",
            "content": f"Auto-selected top {len(top_matches)} matches",
        }],
    }
```

**Routing Functions:**

```python
def route_after_search(state: ImpactAssessmentState) -> str:
    """Route based on search results."""
    if state.get("status") == "error":
        return "error_handler"
    return "auto_select"

def route_after_auto_select(state: ImpactAssessmentState) -> str:
    """Route based on auto-selection results."""
    if state.get("status") == "error":
        return "error_handler"
    if not state.get("selected_matches"):
        return END  # No matches = can't continue
    return "modules"

def route_after_agent(state: ImpactAssessmentState) -> str:
    """Generic routing after agent execution."""
    if state.get("status") == "error":
        return "error_handler"
    next_agent = state.get("current_agent", "done")
    if next_agent == "done":
        return END
    return next_agent
```

---

### 3. Service (`service.py`)

Orchestrates pipeline execution.

```python
from pydantic import BaseModel
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
    modules_output: Dict | None = None
    effort_output: Dict | None = None
    stories_output: Dict | None = None
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
```

**Process Method:**

```python
async def process(self, request: PipelineRequest) -> PipelineResponse:
    """Run full impact assessment pipeline."""
    # Build initial state
    initial_state: ImpactAssessmentState = {
        "session_id": request.session_id,
        "requirement_text": request.requirement_text,
        "jira_epic_id": request.jira_epic_id,
        "selected_matches": request.selected_matches,
        "status": "created",
        "current_agent": "requirement",
        "messages": [],
    }

    # Execute workflow
    final_state = await self.workflow.ainvoke(initial_state)

    # Save final summary to audit trail
    audit = AuditTrailManager(request.session_id)
    audit.save_json("final_summary.json", {
        "session_id": request.session_id,
        "status": final_state.get("status"),
        "completed_at": datetime.now().isoformat(),
        "modules": final_state.get("modules_output"),
        "effort": final_state.get("effort_output"),
        "stories": final_state.get("stories_output"),
        "code_impact": final_state.get("code_impact_output"),
        "risks": final_state.get("risks_output"),
    })

    return PipelineResponse(
        session_id=request.session_id,
        status=final_state.get("status", "unknown"),
        modules_output=final_state.get("modules_output"),
        effort_output=final_state.get("effort_output"),
        stories_output=final_state.get("stories_output"),
        code_impact_output=final_state.get("code_impact_output"),
        risks_output=final_state.get("risks_output"),
        messages=final_state.get("messages", []),
        error_message=final_state.get("error_message"),
    )
```

---

### 4. Router (`router.py`)

FastAPI endpoints.

```python
router = APIRouter(prefix="/impact", tags=["Impact Analysis"])

@router.post("/run-pipeline", response_model=PipelineResponse)
async def run_pipeline(request: PipelineRequest) -> PipelineResponse:
    """Run full impact assessment pipeline."""
    try:
        service = get_service()
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())

@router.get("/{session_id}/summary")
async def get_summary(session_id: str) -> Dict[str, Any]:
    """Get impact assessment summary for a session."""
    try:
        service = get_service()
        return await service.get_summary(session_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
```

---

## API Reference

### Endpoints

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `POST` | `/impact/run-pipeline` | Run full pipeline | `PipelineResponse` |
| `GET` | `/impact/{session_id}/summary` | Get completed summary | JSON summary |

### Request/Response Examples

**Run Pipeline:**

```bash
curl -X POST http://localhost:8000/impact/run-pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_20240115_103045_a1b2c3",
    "requirement_text": "Build OAuth2 authentication with SSO support...",
    "jira_epic_id": "PROJ-1234"
  }'
```

Response:
```json
{
  "session_id": "sess_20240115_103045_a1b2c3",
  "status": "completed",
  "modules_output": {
    "functional_modules": [...],
    "technical_modules": [...],
    "total_modules": 10
  },
  "effort_output": {
    "total_dev_hours": 160,
    "total_qa_hours": 40,
    "story_points": 34
  },
  "stories_output": {
    "stories": [...],
    "total_stories": 10
  },
  "code_impact_output": {
    "files": [...],
    "total_files": 12
  },
  "risks_output": {
    "risks": [...],
    "high_severity_count": 2
  },
  "messages": [
    {"role": "requirement", "content": "Extracted 14 keywords"},
    {"role": "search", "content": "Found 10 similar projects"},
    {"role": "auto_select", "content": "Auto-selected top 5 matches"},
    ...
  ]
}
```

---

## State Transitions

```
┌─────────────────────────────────────────────────────────────┐
│                    STATE MACHINE                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐                                                │
│  │ created │ (initial state)                                │
│  └────┬────┘                                                │
│       │ requirement_agent                                    │
│       ▼                                                      │
│  ┌───────────────────┐                                      │
│  │requirement_submitted│                                     │
│  └─────────┬─────────┘                                      │
│            │ search_agent                                    │
│            ▼                                                 │
│  ┌─────────────────┐                                        │
│  │  matches_found  │                                        │
│  └────────┬────────┘                                        │
│           │ auto_select_node                                 │
│           ▼                                                  │
│  ┌────────────────────┐                                     │
│  │  matches_selected  │                                     │
│  └─────────┬──────────┘                                     │
│            │ modules → effort → stories → code → risks      │
│            ▼                                                 │
│  ┌──────────────────┐                                       │
│  │generating_impact │ (intermediate states per agent)       │
│  └────────┬─────────┘                                       │
│           │ risks_agent completes                           │
│           ▼                                                  │
│  ┌───────────┐                                              │
│  │ completed │ (terminal state)                             │
│  └───────────┘                                              │
│                                                              │
│  Any node can transition to:                                │
│  ┌─────────┐                                                │
│  │  error  │ → error_handler → END                          │
│  └─────────┘                                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Audit Trail Output

After pipeline completion:

```
data/sessions/2024-01-15/sess_20240115_103045_a1b2c3/
├── final_summary.json           # Complete output aggregation
├── step1_input/
│   ├── requirement.json
│   └── extracted_keywords.json
├── step2_search/
│   ├── search_request.json
│   ├── all_matches.json
│   └── selected_matches.json
└── step3_agents/
    ├── agent_modules/
    ├── agent_effort/
    ├── agent_stories/
    ├── agent_code/
    └── agent_risks/
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Pipeline stuck | Agent infinite loop | Check `current_agent` routing |
| Missing output | Agent exception | Check `error_message` in response |
| `TypeError` in state | Invalid partial return | Ensure agent returns `Dict[str, Any]` |
| Workflow not compiling | Invalid graph edges | Verify all nodes exist before wiring |

---

## Best Practices

1. **Return partial state only** - Don't reconstruct full state in agents
2. **Set `current_agent`** - Always indicate the next node
3. **Handle errors gracefully** - Route to `error_handler`, don't crash
4. **Log messages** - Add to `messages` list for observability
5. **Use `total=False`** - Enables cleaner partial updates
