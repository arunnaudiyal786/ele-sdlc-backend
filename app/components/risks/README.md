# Risks Component

The **risks** component is an LLM-powered agent that identifies potential risks and provides mitigation strategies. It's the final analysis step in the pipeline, synthesizing all previous outputs to produce a comprehensive risk assessment.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      RISKS COMPONENT                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌───────────────────┐                    │
│  │   Router     │─────▶│   RisksService    │                    │
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
│                        │  • Code summary     │                   │
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
│                        │   Risk Assessment   │                   │
│                        │  • Severity         │                   │
│                        │  • Likelihood       │                   │
│                        │  • Mitigation       │                   │
│                        └─────────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
risks/
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

Defines the data contracts for risk identification.

```python
from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime

class RiskItem(BaseModel):
    """Single risk with mitigation."""
    title: str
    description: str = ""
    severity: str = "MEDIUM"
    likelihood: str = "MEDIUM"
    category: str = "Technical"
    mitigation: str = ""

class RisksRequest(BaseModel):
    """Request for risk identification."""
    session_id: str
    requirement_text: str
    selected_matches: List[Dict]
    modules_output: Dict
    effort_output: Dict
    code_impact_output: Dict

class RisksResponse(BaseModel):
    """Response with identified risks."""
    session_id: str
    agent: str = "risks"
    risks: List[RiskItem]
    total_risks: int
    high_severity_count: int
    generated_at: datetime
```

**Risk Categories:**

| Category | Description | Example |
|----------|-------------|---------|
| `Technical` | Technology/implementation risks | "OAuth2 library compatibility issues" |
| `Schedule` | Timeline risks | "Dependency on external IDP availability" |
| `Resource` | Team/skills risks | "Requires security expertise not on team" |
| `Integration` | External system risks | "Third-party API rate limits" |
| `Security` | Security/compliance risks | "Token storage vulnerabilities" |

**Risk Matrix:**

```
            LIKELIHOOD
           LOW    MEDIUM    HIGH
        ┌────────────────────────┐
    LOW │  Low   │  Low    │Medium│
S       ├────────┼─────────┼──────┤
E MEDIUM│  Low   │ Medium  │ High │
V       ├────────┼─────────┼──────┤
   HIGH │ Medium │  High   │ High │
        └────────────────────────┘
```

---

### 2. Prompts (`prompts.py`)

LLM prompt templates for risk identification.

```python
RISKS_SYSTEM_PROMPT = """You are an expert risk analyst for software projects.

Given a requirement, impacted modules, effort estimates, and code impact, identify risks.

OUTPUT FORMAT (JSON only, no markdown):
{
  "risks": [
    {
      "title": "string",
      "description": "string",
      "severity": "HIGH|MEDIUM|LOW",
      "likelihood": "HIGH|MEDIUM|LOW",
      "category": "Technical|Schedule|Resource|Integration|Security",
      "mitigation": "string"
    }
  ]
}

Identify exactly 5 risks with actionable mitigations."""

RISKS_USER_PROMPT = """REQUIREMENT:
{requirement_description}

IMPACTED MODULES:
{modules_summary}

EFFORT ESTIMATE:
{effort_summary}

CODE IMPACT:
{code_summary}

Identify the top 5 risks for this implementation."""
```

**Risk Identification Guidelines:**

- Focus on **project-specific** risks, not generic ones
- Include at least one risk from each major category
- Mitigations should be **actionable** and specific
- HIGH severity risks should have detailed mitigations

---

### 3. Service (`service.py`)

Core business logic for risk identification.

```python
class RisksService(BaseComponent[RisksRequest, RisksResponse]):
    """Risk identification agent as a component."""

    def __init__(self):
        self.ollama = get_ollama_client()

    @property
    def component_name(self) -> str:
        return "risks"
```

**Process Method:**

```python
async def process(self, request: RisksRequest) -> RisksResponse:
    """Identify risks using LLM."""
    # Summarize all previous outputs
    modules_summary = self._format_modules(request.modules_output)
    effort_summary = self._format_effort(request.effort_output)
    code_summary = self._format_code(request.code_impact_output)

    user_prompt = RISKS_USER_PROMPT.format(
        requirement_description=request.requirement_text,
        modules_summary=modules_summary,
        effort_summary=effort_summary,
        code_summary=code_summary,
    )

    audit = AuditTrailManager(request.session_id)
    audit.save_text(
        "input_prompt.txt",
        f"{RISKS_SYSTEM_PROMPT}\n\n{user_prompt}",
        subfolder="step3_agents/agent_risks"
    )

    raw_response = await self.ollama.generate(
        system_prompt=RISKS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        format="json",
    )

    audit.save_text("raw_response.txt", raw_response, subfolder="step3_agents/agent_risks")

    parsed = self._parse_response(raw_response)
    risks = [RiskItem(**r) for r in parsed.get("risks", [])]
    high_count = sum(1 for r in risks if r.severity == "HIGH")

    response = RisksResponse(
        session_id=request.session_id,
        risks=risks,
        total_risks=len(risks),
        high_severity_count=high_count,
        generated_at=datetime.now(),
    )

    audit.save_json("parsed_output.json", response.model_dump(), subfolder="step3_agents/agent_risks")
    audit.add_step_completed("risks_identified")

    return response
```

**Context Formatting:**

```python
def _format_modules(self, modules_output: Dict) -> str:
    """Format modules for prompt."""
    total = modules_output.get("total_modules", 0)
    high_impact = sum(
        1 for m in
        modules_output.get("functional_modules", []) +
        modules_output.get("technical_modules", [])
        if m.get("impact") == "HIGH"
    )
    return f"{total} modules identified, {high_impact} high-impact"

def _format_effort(self, effort_output: Dict) -> str:
    """Format effort for prompt."""
    return (
        f"{effort_output.get('total_hours', 0)} hours, "
        f"{effort_output.get('story_points', 0)} points, "
        f"{effort_output.get('confidence', 'N/A')} confidence"
    )

def _format_code(self, code_output: Dict) -> str:
    """Format code impact for prompt."""
    return (
        f"{code_output.get('total_files', 0)} files across "
        f"{len(code_output.get('repositories_affected', []))} repositories"
    )
```

---

### 4. Agent (`agent.py`)

LangGraph node wrapper - **the final agent in the pipeline**.

```python
async def risks_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for risk identification."""
    try:
        service = get_service()

        request = RisksRequest(
            session_id=state["session_id"],
            requirement_text=state["requirement_text"],
            selected_matches=state.get("selected_matches", []),
            modules_output=state.get("modules_output", {}),
            effort_output=state.get("effort_output", {}),
            code_impact_output=state.get("code_impact_output", {}),
        )

        response = await service.process(request)

        return {
            "risks_output": response.model_dump(),
            "status": "completed",  # Final status
            "current_agent": "done",  # Signals workflow completion
            "messages": [
                {
                    "role": "risks",
                    "content": f"Identified {response.total_risks} risks ({response.high_severity_count} high severity)",
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

**Note:** This is the terminal agent - it sets `status: "completed"` and `current_agent: "done"`.

---

## API Reference

### Endpoints

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `POST` | `/impact/generate/risks` | Identify project risks | `RisksResponse` |

### Request/Response Examples

**Generate Risk Assessment:**

```bash
curl -X POST http://localhost:8000/impact/generate/risks \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_20240115_103045_a1b2c3",
    "requirement_text": "Build OAuth2 authentication with SSO support...",
    "selected_matches": [...],
    "modules_output": {...},
    "effort_output": {...},
    "code_impact_output": {...}
  }'
```

Response:
```json
{
  "session_id": "sess_20240115_103045_a1b2c3",
  "agent": "risks",
  "risks": [
    {
      "title": "OAuth2 Library Compatibility",
      "description": "Selected OAuth2 library may have compatibility issues with existing FastAPI middleware",
      "severity": "HIGH",
      "likelihood": "MEDIUM",
      "category": "Technical",
      "mitigation": "Conduct spike to validate library integration before main development; prepare fallback library option"
    },
    {
      "title": "IDP Configuration Delays",
      "description": "External identity provider setup may require lengthy approval process",
      "severity": "MEDIUM",
      "likelihood": "HIGH",
      "category": "Schedule",
      "mitigation": "Start IDP onboarding process immediately; use mock IDP for development"
    },
    {
      "title": "Security Review Requirements",
      "description": "Authentication changes require security team review which may extend timeline",
      "severity": "MEDIUM",
      "likelihood": "MEDIUM",
      "category": "Schedule",
      "mitigation": "Engage security team early; schedule review sessions in parallel with development"
    },
    {
      "title": "Token Storage Security",
      "description": "Improper token storage could lead to security vulnerabilities",
      "severity": "HIGH",
      "likelihood": "LOW",
      "category": "Security",
      "mitigation": "Follow OWASP guidelines; use encrypted storage; implement token rotation"
    },
    {
      "title": "API Rate Limits",
      "description": "Third-party IDP API rate limits may affect peak load handling",
      "severity": "LOW",
      "likelihood": "MEDIUM",
      "category": "Integration",
      "mitigation": "Implement token caching; design graceful degradation for rate limit scenarios"
    }
  ],
  "total_risks": 5,
  "high_severity_count": 2,
  "generated_at": "2024-01-15T10:30:45.123456"
}
```

---

## LLM Output Format

The LLM is instructed to return:

```json
{
  "risks": [
    {
      "title": "Brief risk title",
      "description": "Detailed description of the risk",
      "severity": "HIGH|MEDIUM|LOW",
      "likelihood": "HIGH|MEDIUM|LOW",
      "category": "Technical|Schedule|Resource|Integration|Security",
      "mitigation": "Actionable steps to mitigate the risk"
    }
  ]
}
```

---

## Audit Trail Output

```
data/sessions/2024-01-15/sess_20240115_103045_a1b2c3/
└── step3_agents/
    └── agent_risks/
        ├── input_prompt.txt     # Full context from all previous agents
        ├── raw_response.txt     # Raw LLM output
        └── parsed_output.json   # Validated RisksResponse
```

---

## Integration with Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    WORKFLOW POSITION                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐      ┌──────────┐      ┌─────────┐         │
│  │ code_impact │─────▶│  risks   │─────▶│   END   │         │
│  │             │      │  (HERE)  │      │         │         │
│  └─────────────┘      └──────────┘      └─────────┘         │
│                                                              │
│  Input: ALL previous outputs (modules, effort, code)         │
│  Output: risks_output                                        │
│  Next: status = "completed", current_agent = "done"          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Generic risks | Not enough context | Review input summaries |
| Missing mitigations | LLM didn't complete | Check raw response length |
| Too many HIGH | Overly conservative | Review and calibrate |
| Empty category | Invalid category value | Check against allowed values |

---

## Best Practices

1. **Review high-severity risks** - Ensure mitigations are actionable
2. **Cross-check categories** - Ensure diversity across risk types
3. **Validate mitigations** - Should be specific, not generic advice
4. **Track risk evolution** - Compare with post-implementation actuals
5. **Prioritize by severity × likelihood** - Focus on high-impact risks
