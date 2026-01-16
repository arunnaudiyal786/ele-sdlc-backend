# Stories Component

The **stories** component is an LLM-powered agent that generates Jira-ready user stories based on the requirement, identified modules, and effort estimates. It produces structured stories with acceptance criteria, story points, and priorities.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     STORIES COMPONENT                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌───────────────────┐                    │
│  │   Router     │─────▶│  StoriesService   │                    │
│  │  (FastAPI)   │      │  (BaseComponent)  │                    │
│  └──────────────┘      └─────────┬─────────┘                    │
│                                  │                               │
│  ┌──────────────┐                │                               │
│  │   Agent      │◀───────────────┤                               │
│  │ (LangGraph)  │                │                               │
│  └──────────────┘                │                               │
│                                  ▼                               │
│                        ┌─────────────────────┐                   │
│                        │   Context Building  │                   │
│                        │  • Requirement      │                   │
│                        │  • Modules summary  │                   │
│                        │  • Effort summary   │                   │
│                        └─────────┬───────────┘                   │
│                                  │                               │
│                                  ▼                               │
│                        ┌─────────────────────┐                   │
│                        │   Ollama Client     │                   │
│                        │  (LLM Generation)   │                   │
│                        └─────────┬───────────┘                   │
│                                  │                               │
│                                  ▼                               │
│                        ┌─────────────────────┐                   │
│                        │   Jira Stories      │                   │
│                        │  • Title            │                   │
│                        │  • Story Points     │                   │
│                        │  • Acceptance Crit. │                   │
│                        └─────────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
stories/
├── __init__.py      # Public exports
├── models.py        # Pydantic request/response schemas
├── service.py       # LLM invocation and response parsing
├── prompts.py       # System and user prompt templates
├── agent.py         # LangGraph node wrapper
├── router.py        # FastAPI endpoints
└── README.md        # This file
```

## Code Walkthrough

### 1. Models (`models.py`)

Defines the data contracts for story generation.

```python
from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime

class JiraStoryItem(BaseModel):
    """Single Jira story."""
    story_id: str = Field(default="")
    title: str
    description: str = Field(default="")
    story_type: str = Field(..., pattern="^(Story|Task|Bug|Spike)$")
    story_points: int = Field(..., ge=1, le=13)
    acceptance_criteria: List[str]
    priority: str = Field(..., pattern="^(HIGH|MEDIUM|LOW)$")
    labels: List[str] = Field(default_factory=list)

class JiraStoriesRequest(BaseModel):
    """Request to generate Jira stories."""
    session_id: str
    requirement_text: str
    selected_matches: List[Dict]
    impacted_modules_output: Dict
    estimation_effort_output: Dict
    tdd_output: Dict

class JiraStoriesResponse(BaseModel):
    """Response with generated stories."""
    session_id: str
    agent: str = "jira_stories"
    stories: List[JiraStoryItem]
    story_count: int
    total_story_points: int
    generated_at: datetime
```

**Story Types:**

| Type | Purpose | Example |
|------|---------|---------|
| `Story` | User-facing feature | "As a user, I can log in with SSO" |
| `Task` | Technical work | "Configure OAuth2 middleware" |
| `Bug` | Defect fix | "Fix token refresh race condition" |
| `Spike` | Research/investigation | "Investigate IDP compatibility" |

**Story Point Constraints:**

- `ge=1`: Minimum 1 point
- `le=13`: Maximum 13 points (Fibonacci scale cap)
- Stories > 13 should be split

---

### 2. Prompts (`prompts.py`)

LLM prompt templates for story generation.

```python
STORIES_SYSTEM_PROMPT = """You are an expert Agile project manager creating Jira stories.

Given a requirement, impacted modules, and effort estimates, generate user stories.

OUTPUT FORMAT (JSON only, no markdown):
{
  "stories": [
    {
      "title": "string",
      "story_type": "Story|Task|Bug|Spike",
      "story_points": 1-13,
      "acceptance_criteria": ["string"],
      "priority": "HIGH|MEDIUM|LOW"
    }
  ]
}

Generate exactly 10 stories that cover the full implementation."""

STORIES_USER_PROMPT = """REQUIREMENT:
{requirement_description}

IMPACTED MODULES:
{modules_summary}

EFFORT ESTIMATE:
{effort_summary}

Generate 10 Jira stories to implement this requirement."""
```

**Story Generation Guidelines:**

- Stories should be **vertical slices** (end-to-end functionality)
- Include 1-2 Spikes for research if technologies are new
- High-priority items should come first
- Acceptance criteria should be testable

---

### 3. Service (`service.py`)

Core business logic for story generation.

```python
class JiraStoriesService(BaseComponent[JiraStoriesRequest, JiraStoriesResponse]):
    """Jira stories generation agent as a component."""

    def __init__(self):
        self.ollama = get_ollama_client()

    @property
    def component_name(self) -> str:
        return "jira_stories"
```

**Process Method:**

```python
async def process(self, request: JiraStoriesRequest) -> JiraStoriesResponse:
    """Generate Jira stories using LLM."""
    modules_summary = self._format_modules(request.impacted_modules_output)
    effort_summary = self._format_effort(request.estimation_effort_output)
    tdd_summary = self._format_tdd(request.tdd_output)

    user_prompt = JIRA_STORIES_USER_PROMPT.format(
        requirement_description=request.requirement_text,
        modules_summary=modules_summary,
        tdd_summary=tdd_summary,
        effort_summary=effort_summary,
    )

    audit = AuditTrailManager(request.session_id)
    audit.save_text(
        "input_prompt.txt",
        f"{JIRA_STORIES_SYSTEM_PROMPT}\n\n{user_prompt}",
        subfolder="step3_agents/agent_jira_stories"
    )

    raw_response = await self.ollama.generate(
        system_prompt=JIRA_STORIES_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        format="json",
    )

    audit.save_text("raw_response.txt", raw_response, subfolder="step3_agents/agent_jira_stories")

    parsed = self._parse_response(raw_response)
    stories = [JiraStoryItem(**s) for s in parsed.get("stories", [])]
    total_points = sum(s.story_points for s in stories)

    response = JiraStoriesResponse(
        session_id=request.session_id,
        stories=stories,
        story_count=len(stories),
        total_story_points=total_points,
        generated_at=datetime.now(),
    )

    audit.save_json("parsed_output.json", response.model_dump(), subfolder="step3_agents/agent_jira_stories")
    audit.add_step_completed("jira_stories_generated")

    return response
```

**Context Formatting:**

```python
def _format_modules(self, modules_output: Dict) -> str:
    """Format modules for prompt."""
    lines = []
    for m in modules_output.get("functional_modules", [])[:5]:
        lines.append(f"- {m.get('name')}")
    return "\n".join(lines) if lines else "No modules."

def _format_effort(self, effort_output: Dict) -> str:
    """Format effort for prompt."""
    return (
        f"Dev: {effort_output.get('total_dev_hours', 0)}h, "
        f"QA: {effort_output.get('total_qa_hours', 0)}h, "
        f"Points: {effort_output.get('story_points', 0)}"
    )
```

---

### 4. Agent (`agent.py`)

LangGraph node wrapper.

```python
async def jira_stories_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for Jira stories generation."""
    try:
        service = get_service()

        request = JiraStoriesRequest(
            session_id=state["session_id"],
            requirement_text=state["requirement_text"],
            selected_matches=state.get("selected_matches", []),
            impacted_modules_output=state.get("impacted_modules_output", {}),
            estimation_effort_output=state.get("estimation_effort_output", {}),
            tdd_output=state.get("tdd_output", {}),
        )

        response = await service.process(request)

        return {
            "jira_stories_output": response.model_dump(),
            "status": "jira_stories_generated",
            "current_agent": "code_impact",
            "messages": [
                {
                    "role": "jira_stories",
                    "content": f"Generated {response.story_count} Jira stories ({response.total_story_points} points)",
                }
            ],
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler",
        }
```

---

## API Reference

### Endpoints

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `POST` | `/api/v1/jira-stories` | Generate Jira stories | `JiraStoriesResponse` |

### Request/Response Examples

**Generate Jira Stories:**

```bash
curl -X POST http://localhost:8000/api/v1/jira-stories \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-xxxx-yyyy",
    "requirement_text": "Build OAuth2 authentication with SSO support...",
    "selected_matches": [...],
    "impacted_modules_output": {...},
    "estimation_effort_output": {"total_dev_hours": 160, "total_qa_hours": 40, "story_points": 34},
    "tdd_output": {...}
  }'
```

Response:
```json
{
  "session_id": "session-xxxx-yyyy",
  "agent": "jira_stories",
  "stories": [
    {
      "story_id": "STORY-001",
      "title": "Implement OAuth2 authorization code flow",
      "description": "As a user, I want to authenticate via OAuth2 so that I can securely access the system.",
      "story_type": "Story",
      "story_points": 5,
      "acceptance_criteria": [
        "User can initiate OAuth2 login",
        "Authorization code is exchanged for tokens",
        "Access token is securely stored"
      ],
      "priority": "HIGH",
      "labels": []
    },
    {
      "story_id": "STORY-002",
      "title": "Configure SSO identity provider integration",
      "description": "As an admin, I want to configure SSO so that users can login with corporate credentials.",
      "story_type": "Task",
      "story_points": 3,
      "acceptance_criteria": [
        "IDP metadata is configured",
        "SAML assertions are validated",
        "User attributes are mapped correctly"
      ],
      "priority": "HIGH",
      "labels": []
    },
    {
      "story_id": "STORY-003",
      "title": "Research token refresh strategies",
      "description": "Investigate different token refresh approaches to determine the best strategy.",
      "story_type": "Spike",
      "story_points": 2,
      "acceptance_criteria": [
        "Document refresh token patterns",
        "Evaluate silent refresh vs. explicit refresh",
        "Recommend approach for mobile clients"
      ],
      "priority": "MEDIUM",
      "labels": []
    }
  ],
  "story_count": 10,
  "total_story_points": 34,
  "generated_at": "2026-01-15T10:30:45.123456"
}
```

---

## LLM Output Format

The LLM is instructed to return:

```json
{
  "stories": [
    {
      "title": "Clear, actionable story title",
      "story_type": "Story|Task|Bug|Spike",
      "story_points": 1-13,
      "acceptance_criteria": [
        "Testable criterion 1",
        "Testable criterion 2"
      ],
      "priority": "HIGH|MEDIUM|LOW"
    }
  ]
}
```

---

## Story Point Alignment

The total story points from generated stories should approximately match the effort estimate:

```
effort_output.story_points ≈ Σ(story.story_points for each story)
```

| Effort Points | Expected Stories | Distribution |
|---------------|------------------|--------------|
| ~34 points | 10 stories | 3-4 HIGH, 4-5 MEDIUM, 2-3 LOW |
| ~55 points | 10-12 stories | May need to split |
| ~13 points | 5-7 stories | Smaller scope |

---

## Audit Trail Output

```
sessions/2026-01-15-HHMM/session-xxxx-yyyy/
└── step3_agents/
    └── agent_jira_stories/
        ├── input_prompt.txt     # Full prompt with modules + effort + TDD
        ├── raw_response.txt     # Raw LLM output
        └── parsed_output.json   # Validated JiraStoriesResponse
```

---

## Integration with Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    WORKFLOW POSITION                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐      ┌─────────────┐      ┌─────────────┐     │
│  │   tdd    │─────▶│ jira_stories│─────▶│ code_impact │──▶..│
│  │          │      │   (HERE)    │      │             │     │
│  └──────────┘      └─────────────┘      └─────────────┘     │
│                                                              │
│  Input: requirement_text, impacted_modules_output,           │
│         estimation_effort_output, tdd_output                 │
│  Output: jira_stories_output                                 │
│  Next: current_agent = "code_impact"                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Points don't align | LLM didn't consider effort | Review effort summary in prompt |
| Too few stories | LLM returned < 10 | Adjust prompt to be more specific |
| Missing AC | Empty acceptance_criteria | Check LLM response format |
| Invalid story_type | Not in enum | Pydantic will reject; check raw response |

---

## Best Practices

1. **Review generated stories** - LLM output needs human validation
2. **Check point distribution** - HIGH priority should have proportional points
3. **Verify acceptance criteria** - Should be specific and testable
4. **Split large stories** - Stories > 8 points often need breakdown
5. **Include technical tasks** - Not everything is a user Story
