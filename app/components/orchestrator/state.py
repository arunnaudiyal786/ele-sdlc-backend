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

    # SEARCH RESULTS - Set by historical_match component
    all_matches: List[Dict]
    selected_matches: List[Dict]

    # AGENT OUTPUTS - Set by each agent component
    impacted_modules_output: Dict
    estimation_effort_output: Dict
    tdd_output: Dict
    jira_stories_output: Dict
    code_impact_output: Dict
    risks_output: Dict

    # CONTROL FIELDS - Updated throughout workflow
    status: Literal[
        "created",
        "requirement_submitted",
        "matches_found",
        "matches_selected",
        "impacted_modules_generated",
        "estimation_effort_completed",
        "tdd_generated",
        "jira_stories_generated",
        "code_impact_generated",
        "risks_generated",
        "completed",
        "error",
    ]
    current_agent: str
    error_message: Optional[str]

    # TIMING & AUDIT
    timing: Dict[str, int]

    # Accumulated messages (uses operator.add reducer)
    messages: Annotated[List[Dict], operator.add]
