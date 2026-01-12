# Code Impact Component

The **code_impact** component is an LLM-powered agent that identifies specific code files that will be impacted by the requirement. It analyzes modules and stories to predict which files need creation, modification, or deletion across repositories.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   CODE IMPACT COMPONENT                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌────────────────────┐                   │
│  │   Router     │─────▶│ CodeImpactService  │                   │
│  │  (FastAPI)   │      │  (BaseComponent)   │                   │
│  └──────────────┘      └─────────┬──────────┘                   │
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
│                        │  • Stories summary  │                   │
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
│                        │   Code Files        │                   │
│                        │  • File paths       │                   │
│                        │  • Change types     │                   │
│                        │  • Languages        │                   │
│                        └─────────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
code_impact/
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

Defines the data contracts for code impact analysis.

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

class CodeFile(BaseModel):
    """Single impacted code file."""
    file_path: str
    repository: str
    change_type: str = Field(..., pattern="^(CREATE|MODIFY|DELETE)$")
    language: str
    reason: str
    estimated_lines: Optional[int] = None

class CodeImpactRequest(BaseModel):
    """Request for code impact analysis."""
    session_id: str
    requirement_text: str
    selected_matches: List[Dict]
    modules_output: Dict
    stories_output: Dict

class CodeImpactResponse(BaseModel):
    """Response with code impact analysis."""
    session_id: str
    agent: str = "code_impact"
    files: List[CodeFile]
    total_files: int
    repositories_affected: List[str]
    generated_at: datetime
```

**Change Types:**

| Type | Description | Example |
|------|-------------|---------|
| `CREATE` | New file needed | `src/auth/oauth_handler.py` |
| `MODIFY` | Existing file changes | `src/api/routes.py` |
| `DELETE` | File removal | `src/auth/legacy_login.py` |

---

### 2. Prompts (`prompts.py`)

LLM prompt templates for code impact analysis.

```python
CODE_IMPACT_SYSTEM_PROMPT = """You are an expert software architect analyzing code impact.

Given a requirement, impacted modules, and generated stories, identify affected code files.

OUTPUT FORMAT (JSON only, no markdown):
{
  "files": [
    {
      "file_path": "src/path/to/file.py",
      "repository": "repo-name",
      "change_type": "CREATE|MODIFY|DELETE",
      "language": "Python|TypeScript|Java|etc",
      "reason": "string",
      "estimated_lines": integer
    }
  ]
}

Identify 8-12 files that would be impacted."""

CODE_IMPACT_USER_PROMPT = """REQUIREMENT:
{requirement_description}

IMPACTED MODULES:
{modules_summary}

GENERATED STORIES:
{stories_summary}

Identify the code files that would be impacted by this requirement."""
```

---

### 3. Service (`service.py`)

Core business logic for code impact analysis.

```python
class CodeImpactService(BaseComponent[CodeImpactRequest, CodeImpactResponse]):
    """Code impact analysis agent as a component."""

    def __init__(self):
        self.ollama = get_ollama_client()

    @property
    def component_name(self) -> str:
        return "code_impact"
```

**Process Method:**

```python
async def process(self, request: CodeImpactRequest) -> CodeImpactResponse:
    """Analyze code impact using LLM."""
    modules_summary = self._format_modules(request.modules_output)
    stories_summary = self._format_stories(request.stories_output)

    user_prompt = CODE_IMPACT_USER_PROMPT.format(
        requirement_description=request.requirement_text,
        modules_summary=modules_summary,
        stories_summary=stories_summary,
    )

    audit = AuditTrailManager(request.session_id)
    audit.save_text(
        "input_prompt.txt",
        f"{CODE_IMPACT_SYSTEM_PROMPT}\n\n{user_prompt}",
        subfolder="step3_agents/agent_code"
    )

    raw_response = await self.ollama.generate(
        system_prompt=CODE_IMPACT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        format="json",
    )

    audit.save_text("raw_response.txt", raw_response, subfolder="step3_agents/agent_code")

    parsed = self._parse_response(raw_response)
    files = [CodeFile(**f) for f in parsed.get("files", [])]
    repos = list(set(f.repository for f in files))  # Unique repositories

    response = CodeImpactResponse(
        session_id=request.session_id,
        files=files,
        total_files=len(files),
        repositories_affected=repos,
        generated_at=datetime.now(),
    )

    audit.save_json("parsed_output.json", response.model_dump(), subfolder="step3_agents/agent_code")
    audit.add_step_completed("code_impact_analyzed")

    return response
```

**Context Formatting:**

```python
def _format_modules(self, modules_output: Dict) -> str:
    """Format modules for prompt."""
    lines = []
    for m in modules_output.get("functional_modules", []):
        lines.append(f"- {m.get('name')}")
    for m in modules_output.get("technical_modules", []):
        lines.append(f"- {m.get('name')}")
    return "\n".join(lines) if lines else "No modules."

def _format_stories(self, stories_output: Dict) -> str:
    """Format stories for prompt."""
    lines = []
    for s in stories_output.get("stories", [])[:5]:  # Top 5 stories
        lines.append(f"- {s.get('title')}")
    return "\n".join(lines) if lines else "No stories."
```

---

### 4. Agent (`agent.py`)

LangGraph node wrapper.

```python
async def code_impact_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for code impact analysis."""
    try:
        service = get_service()

        request = CodeImpactRequest(
            session_id=state["session_id"],
            requirement_text=state["requirement_text"],
            selected_matches=state.get("selected_matches", []),
            modules_output=state.get("modules_output", {}),
            stories_output=state.get("stories_output", {}),
        )

        response = await service.process(request)

        return {
            "code_impact_output": response.model_dump(),
            "status": "code_impact_analyzed",
            "current_agent": "risks",  # Final agent
            "messages": [
                {
                    "role": "code_impact",
                    "content": f"Identified {response.total_files} impacted files across {len(response.repositories_affected)} repos",
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
| `POST` | `/impact/generate/code` | Analyze code impact | `CodeImpactResponse` |

### Request/Response Examples

**Generate Code Impact:**

```bash
curl -X POST http://localhost:8000/impact/generate/code \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_20240115_103045_a1b2c3",
    "requirement_text": "Build OAuth2 authentication with SSO support...",
    "selected_matches": [...],
    "modules_output": {...},
    "stories_output": {...}
  }'
```

Response:
```json
{
  "session_id": "sess_20240115_103045_a1b2c3",
  "agent": "code_impact",
  "files": [
    {
      "file_path": "src/auth/oauth_handler.py",
      "repository": "backend-api",
      "change_type": "CREATE",
      "language": "Python",
      "reason": "New OAuth2 authorization code flow handler",
      "estimated_lines": 150
    },
    {
      "file_path": "src/middleware/auth_middleware.py",
      "repository": "backend-api",
      "change_type": "MODIFY",
      "language": "Python",
      "reason": "Add OAuth2 token validation middleware",
      "estimated_lines": 50
    },
    {
      "file_path": "src/components/LoginForm.tsx",
      "repository": "frontend-app",
      "change_type": "MODIFY",
      "language": "TypeScript",
      "reason": "Add SSO login button and redirect logic",
      "estimated_lines": 80
    },
    {
      "file_path": "migrations/001_add_oauth_tokens.sql",
      "repository": "backend-api",
      "change_type": "CREATE",
      "language": "SQL",
      "reason": "Database schema for OAuth token storage",
      "estimated_lines": 30
    }
  ],
  "total_files": 12,
  "repositories_affected": ["backend-api", "frontend-app"],
  "generated_at": "2024-01-15T10:30:45.123456"
}
```

---

## LLM Output Format

The LLM is instructed to return:

```json
{
  "files": [
    {
      "file_path": "src/path/to/file.ext",
      "repository": "repo-name",
      "change_type": "CREATE|MODIFY|DELETE",
      "language": "Python|TypeScript|Java|SQL|etc",
      "reason": "Why this file is impacted",
      "estimated_lines": 150
    }
  ]
}
```

---

## File Path Conventions

The LLM should generate realistic file paths:

| Repository Type | Path Pattern | Example |
|-----------------|--------------|---------|
| Python Backend | `src/module/file.py` | `src/auth/oauth_handler.py` |
| TypeScript Frontend | `src/components/Component.tsx` | `src/components/LoginForm.tsx` |
| Database | `migrations/NNN_description.sql` | `migrations/001_add_tokens.sql` |
| Configuration | `config/env.yaml` | `config/oauth.yaml` |
| Tests | `tests/test_module.py` | `tests/test_oauth.py` |

---

## Audit Trail Output

```
data/sessions/2024-01-15/sess_20240115_103045_a1b2c3/
└── step3_agents/
    └── agent_code/
        ├── input_prompt.txt     # Full prompt with modules + stories
        ├── raw_response.txt     # Raw LLM output
        └── parsed_output.json   # Validated CodeImpactResponse
```

---

## Integration with Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    WORKFLOW POSITION                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐      ┌─────────────┐      ┌──────────┐        │
│  │ stories  │─────▶│ code_impact │─────▶│  risks   │──▶END  │
│  │          │      │   (HERE)    │      │          │        │
│  └──────────┘      └─────────────┘      └──────────┘        │
│                                                              │
│  Input: requirement_text, modules_output, stories_output     │
│  Output: code_impact_output                                  │
│  Next: current_agent = "risks"                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Unrealistic paths | LLM hallucination | Provide more project context |
| Missing repos | Not enough context | Include repo names in prompt |
| Too few files | Underestimation | Adjust prompt to request more |
| Invalid change_type | Not in enum | Pydantic rejects; check raw response |

---

## Best Practices

1. **Review file paths** - LLM may hallucinate non-existent paths
2. **Cross-reference with modules** - Files should align with identified modules
3. **Check language distribution** - Should match technology stack
4. **Validate estimated_lines** - Sanity check for reasonableness
5. **Consider test files** - Don't forget tests for new code
