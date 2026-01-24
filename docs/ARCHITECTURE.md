# Architecture Documentation

Comprehensive guide to the AI Impact Assessment System's design, patterns, and technical decisions.

## Table of Contents

- [System Overview](#system-overview)
- [Component-Based Design](#component-based-design)
- [Core Concepts](#core-concepts)
  - [LangGraph State Management](#langgraph-state-management)
  - [Workflow Pipeline](#workflow-pipeline)
  - [RAG Layer](#rag-layer)
  - [Context Assembly](#context-assembly)
  - [SSE Streaming](#sse-streaming)
  - [Configuration Management](#configuration-management)
  - [Error Handling](#error-handling)
- [Data Flow](#data-flow)
- [Cross-Cutting Concerns](#cross-cutting-concerns)
- [Architecture Decisions](#architecture-decisions)
- [Scalability & Performance](#scalability--performance)

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                     AI Impact Assessment System                       │
│                     FastAPI + LangGraph Backend                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                        REST API Layer                           │  │
│  │  FastAPI routers • Pydantic validation • OpenAPI docs          │  │
│  └────────────┬───────────────────────────────────────────────────┘  │
│               │                                                       │
│  ┌────────────▼───────────────────────────────────────────────────┐  │
│  │                    Component Layer                              │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │  │
│  │  │ Session  │ │Requiremt │ │  Search  │ │ Modules  │  ...    │  │
│  │  │          │ │          │ │          │ │          │         │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │  │
│  │  Each: models.py, service.py, agent.py, router.py             │  │
│  └────────────┬───────────────────────────────────────────────────┘  │
│               │                                                       │
│  ┌────────────▼───────────────────────────────────────────────────┐  │
│  │                    Orchestration Layer                          │  │
│  │  LangGraph workflow • State management • Agent coordination    │  │
│  │                                                                 │  │
│  │  requirement → historical_match → auto_select → modules →      │  │
│  │  estimation → tdd → jira_stories → END                         │  │
│  └────────────┬───────────────────────────────────────────────────┘  │
│               │                                                       │
│  ┌────────────▼───────────────────────────────────────────────────┐  │
│  │                      RAG Layer                                  │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │  │
│  │  │  Embeddings  │ │ Vector Store │ │Hybrid Search │          │  │
│  │  │   (Ollama)   │ │  (ChromaDB)  │ │ (70/30 mix)  │          │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘          │  │
│  └────────────┬───────────────────────────────────────────────────┘  │
│               │                                                       │
│  ┌────────────▼───────────────────────────────────────────────────┐  │
│  │                   External Services                             │  │
│  │  ┌──────────────┐           ┌──────────────┐                  │  │
│  │  │    Ollama    │           │   File I/O   │                  │  │
│  │  │  (Local LLM) │           │ (Audit Trail)│                  │  │
│  │  └──────────────┘           └──────────────┘                  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

**Key Characteristics:**
- **Async-first:** All I/O operations use async/await
- **Type-safe:** Pydantic models throughout
- **Modular:** Component-based architecture
- **Stateful:** LangGraph manages workflow state
- **Auditable:** Complete session audit trails

---

## Component-Based Design

### Design Pattern

Every feature follows the **Component Pattern**:

```
app/components/{name}/
├── __init__.py      # Public API exports
├── models.py        # Pydantic request/response schemas
├── service.py       # Business logic (extends BaseComponent)
├── agent.py         # LangGraph node wrapper
├── router.py        # FastAPI REST endpoints
├── prompts.py       # LLM prompt templates (optional)
└── README.md        # Component documentation
```

### BaseComponent Abstract Class

All services extend `BaseComponent[TRequest, TResponse]`:

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel

TRequest = TypeVar("TRequest", bound=BaseModel)
TResponse = TypeVar("TResponse", bound=BaseModel)


class BaseComponent(ABC, Generic[TRequest, TResponse]):
    """Abstract base for all components."""

    @property
    @abstractmethod
    def component_name(self) -> str:
        """Unique component identifier."""
        pass

    @abstractmethod
    async def process(self, request: TRequest) -> TResponse:
        """Main processing logic."""
        pass

    async def health_check(self) -> dict:
        """Health status check."""
        return {"component": self.component_name, "status": "healthy"}

    async def __call__(self, request: TRequest) -> TResponse:
        """Allow component(request) syntax."""
        return await self.process(request)
```

**Benefits:**
- Enforces consistent interface across components
- Type safety via generics
- Easy to test (mock the interface)
- Self-documenting via type hints

### Component Lifecycle

```
┌──────────────────────────────────────────────────────────────┐
│                   Component Lifecycle                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Request arrives at Router                                │
│     └─→ Pydantic validation                                  │
│                                                               │
│  2. Router calls Service.process()                           │
│     └─→ Business logic execution                             │
│     └─→ External service calls (LLM, DB)                     │
│     └─→ Audit trail saved                                    │
│                                                               │
│  3. Service returns Response                                 │
│     └─→ Pydantic serialization                               │
│                                                               │
│  4. Router returns HTTP response                             │
│     └─→ OpenAPI documentation generated                      │
│                                                               │
│  [Alternative Path: LangGraph]                               │
│                                                               │
│  1. Agent wrapper called by LangGraph                        │
│     └─→ Extracts data from state dict                        │
│                                                               │
│  2. Agent calls Service.process()                            │
│     └─→ Same business logic as REST path                     │
│                                                               │
│  3. Agent returns partial state update                       │
│     └─→ LangGraph merges into full state                     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Component Dependencies

```python
# ❌ Wrong: Direct imports between components
# app/components/tdd/service.py
from app.components.estimation_effort.service import EstimationService  # Tight coupling!

# ✅ Correct: Use state dict or dependency injection
# app/components/tdd/service.py
def process(self, request: TDDRequest) -> TDDResponse:
    # Estimation output already in request (from state)
    estimated_hours = request.estimated_hours
```

Components communicate via:
1. **LangGraph state** (workflow execution)
2. **HTTP requests** (REST API)
3. **Shared utilities** (`app/utils/`, `app/rag/`)

---

## Core Concepts

### LangGraph State Management

#### State Structure

```python
from typing import TypedDict, List, Dict, Any, Annotated
import operator


class ImpactAssessmentState(TypedDict, total=False):
    """Workflow state - represents entire pipeline context.

    Using total=False allows nodes to return PARTIAL updates.
    LangGraph automatically merges partial returns into full state.
    """

    # SESSION CONTEXT - Set at workflow start
    session_id: str
    requirement_text: str
    jira_epic_id: str | None
    extracted_keywords: List[str]

    # SEARCH RESULTS - Set by historical_match component
    all_matches: List[Dict[str, Any]]
    selected_matches: List[Dict[str, Any]]

    # LOADED DOCUMENTS - Set by auto_select node
    # Contains full TDD, estimation, jira_stories for each selected project
    loaded_projects: Dict[str, Dict]  # {project_id: {tdd: {...}, estimation: {...}, jira_stories: {...}}}

    # AGENT OUTPUTS - Set by each agent component
    impacted_modules_output: Dict[str, Any]
    estimation_effort_output: Dict[str, Any]
    tdd_output: Dict[str, Any]
    jira_stories_output: Dict[str, Any]
    code_impact_output: Dict[str, Any]  # Currently disabled
    risks_output: Dict[str, Any]        # Currently disabled

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
        "completed",
        "error",
    ]
    current_agent: str
    error_message: str | None

    # TIMING & AUDIT
    timing: Dict[str, int]

    # Messages (append-only via reducer)
    messages: Annotated[List[Dict[str, Any]], operator.add]
```

#### Partial State Updates

**Critical Pattern:** Agents return **only changed fields**, not full state.

```python
# ✅ Correct: Partial update
async def my_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Returns only what changed."""
    return {
        "my_output": {...},
        "status": "my_step_done",
        "current_agent": "next_agent",
        "messages": [{"role": "my_agent", "content": "..."}],
    }

# ❌ Wrong: Full state replacement
async def my_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """This LOSES all other state fields!"""
    return {
        "session_id": state["session_id"],
        "my_output": {...},
        # ❌ All other fields disappeared!
    }
```

**Why this matters:**
- LangGraph automatically merges partial updates
- Reduces boilerplate (don't copy unchanged fields)
- Prevents accidental state loss
- Enables parallel agent execution (different fields)

#### State Reducers

The `messages` field uses a **reducer** to append instead of replace:

```python
# Definition
messages: Annotated[List[Dict], operator.add]

# Usage in agent
return {
    "messages": [{"role": "agent_name", "content": "New message"}]
}

# LangGraph applies: state["messages"] + [new_message]
# Result: Messages accumulate, not replaced
```

---

### Workflow Pipeline

#### Graph Structure

```python
from langgraph.graph import StateGraph, END
from .state import ImpactAssessmentState

# Create graph
workflow = StateGraph(ImpactAssessmentState)

# Add nodes (agents)
workflow.add_node("requirement", requirement_agent)
workflow.add_node("historical_match", historical_match_agent)
workflow.add_node("auto_select", auto_select_node)  # Loads full documents
workflow.add_node("impacted_modules", impacted_modules_agent)
workflow.add_node("estimation_effort", estimation_effort_agent)
workflow.add_node("tdd", tdd_agent)
workflow.add_node("jira_stories", jira_stories_agent)
workflow.add_node("error_handler", error_handler_node)
# Temporarily disabled:
# workflow.add_node("code_impact", code_impact_agent)
# workflow.add_node("risks", risks_agent)

# Set entry point
workflow.set_entry_point("requirement")

# Wire edges
workflow.add_edge("requirement", "historical_match")
workflow.add_conditional_edges(
    "historical_match",
    route_after_historical_match,
    {"auto_select": "auto_select", "error_handler": "error_handler"},
)
workflow.add_conditional_edges(
    "auto_select",
    route_after_auto_select,
    {"impacted_modules": "impacted_modules", "error_handler": "error_handler", END: END},
)
workflow.add_edge("impacted_modules", "estimation_effort")
workflow.add_edge("estimation_effort", "tdd")
workflow.add_edge("tdd", "jira_stories")
workflow.add_edge("jira_stories", END)
workflow.add_edge("error_handler", END)

# Compile
compiled_workflow = workflow.compile()
```

**Active Pipeline Flow:**
```
requirement → historical_match → auto_select → impacted_modules
           → estimation_effort → tdd → jira_stories → END
```

**Note**: `code_impact` and `risks` agents are implemented but currently disabled in the workflow.

#### Conditional Edges

```python
# Decision function
def route_after_search(state: Dict[str, Any]) -> str:
    """Decide next step based on search results."""
    if len(state.get("all_matches", [])) == 0:
        return END  # No matches, can't proceed
    return "auto_select"

# Add conditional edge
workflow.add_conditional_edges(
    "search",
    route_after_search,
    {
        "auto_select": "auto_select",
        END: END,
    }
)
```

#### Execution

```python
# Run workflow
result = await compiled_workflow.ainvoke(initial_state)

# Result is final state after all agents
assert result["status"] == "completed"
assert "tdd_output" in result
```

#### Error Handling in Workflow

```python
async def safe_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Agent with error handling."""
    try:
        # Business logic
        result = await process_data(state)
        return {
            "my_output": result,
            "status": "my_step_done",
            "current_agent": "next_agent",
        }
    except Exception as e:
        # Return error state (workflow continues)
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler",  # Route to error handler
        }
```

---

### RAG Layer

**Three-Tier Architecture:**

```
┌─────────────────────────────────────────────────────────┐
│                      RAG Layer                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Tier 1: Embeddings (app/rag/embeddings.py)            │
│  ┌────────────────────────────────────────────────────┐ │
│  │  OllamaEmbeddingService                            │ │
│  │  • Singleton pattern                               │ │
│  │  • Model: all-minilm (384 dimensions)             │ │
│  │  • embed_query(text) -> List[float]               │ │
│  │  • embed_documents(texts) -> List[List[float]]    │ │
│  └────────────────────────────────────────────────────┘ │
│                         │                                │
│                         ▼                                │
│  Tier 2: Vector Store (app/rag/vector_store.py)        │
│  ┌────────────────────────────────────────────────────┐ │
│  │  ChromaVectorStore (singleton)                     │ │
│  │  • ChromaDB client wrapper                         │ │
│  │  • Collections:                                    │ │
│  │    - project_index (lightweight metadata)          │ │
│  │    - epics, estimations, tdds, stories            │ │
│  │  • Persistent storage (data/chroma/)               │ │
│  │  • Methods:                                        │ │
│  │    - get_or_create_collection()                   │ │
│  │    - add_documents()                              │ │
│  │    - search()                                     │ │
│  │    - delete_collection()                          │ │
│  └────────────────────────────────────────────────────┘ │
│                         │                                │
│                         ▼                                │
│  Tier 3: Hybrid Search (app/rag/hybrid_search.py)      │
│  ┌────────────────────────────────────────────────────┐ │
│  │  HybridSearchService                               │ │
│  │  • Combines semantic + keyword search              │ │
│  │  • Score fusion: 70% semantic + 30% keyword       │ │
│  │  • BM25 for keyword matching                       │ │
│  │  • Deduplication across collections                │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

#### Singleton Pattern

```python
# Ensures only one instance across application
class VectorStoreManager:
    _instance: "VectorStoreManager | None" = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "VectorStoreManager":
        """Thread-safe singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Double-check
                    cls._instance = cls()
        return cls._instance
```

**Why singletons:**
- ChromaDB client is expensive to initialize
- Embeddings model loaded once in memory
- Consistent state across requests

#### Hybrid Search Algorithm

```python
def hybrid_search(query: str, top_k: int = 10):
    """Combine semantic and keyword search."""

    # 1. Semantic search (vector similarity)
    query_embedding = embedding_service.embed_query(query)
    semantic_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k * 2,  # Over-fetch for fusion
    )

    # 2. Keyword search (BM25)
    keyword_results = bm25_search(query, top_k=top_k * 2)

    # 3. Score normalization (0-1 range)
    semantic_scores = normalize_scores(semantic_results)
    keyword_scores = normalize_scores(keyword_results)

    # 4. Weighted fusion
    final_scores = {}
    for doc_id in set(semantic_scores) | set(keyword_scores):
        s_score = semantic_scores.get(doc_id, 0.0)
        k_score = keyword_scores.get(doc_id, 0.0)

        final_scores[doc_id] = (0.7 * s_score) + (0.3 * k_score)

    # 5. Rank and return top K
    ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]
```

**Tuning weights:**

| Use Case | Semantic | Keyword | Rationale |
|----------|----------|---------|-----------|
| Conceptual queries | 0.8 | 0.2 | Meaning matters more |
| Technical terms | 0.5 | 0.5 | Exact matches important |
| Known keywords | 0.3 | 0.7 | Prefer exact hits |

---

### Context Assembly

The `ContextAssembler` service loads full documents for selected projects after the auto-select step.

#### Project Metadata Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Two-Stage Document Loading                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  STAGE 1: Lightweight Search (project_index collection)             │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Search: requirement_text → project_index                       │ │
│  │  Returns: project_id, project_name, summary, folder_path        │ │
│  │  Purpose: Fast matching without loading full documents          │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                           │                                          │
│                           ▼                                          │
│  STAGE 2: Full Document Loading (top 3 selected projects)           │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  ContextAssembler.load_full_documents()                         │ │
│  │                                                                  │ │
│  │  For each selected project:                                      │ │
│  │  ├── TDDParser.parse(tdd_path) → TDDDocument                    │ │
│  │  ├── EstimationParser.parse(estimation_path) → EstimationDoc    │ │
│  │  └── JiraStoriesParser.parse(jira_path) → JiraStoriesDocument   │ │
│  │                                                                  │ │
│  │  Returns: Dict[project_id, ProjectDocuments]                     │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### Agent-Specific Context

Each agent receives tailored context from the loaded documents:

| Agent | Context Data | Source |
|-------|-------------|--------|
| impacted_modules | module_list, interaction_flow, design_decisions, risks | TDD |
| estimation_effort | task_breakdown, total_points, assumptions_and_risks | Estimation + TDD |
| tdd | design_overview, design_patterns, module_designs, full_text | TDD |
| jira_stories | existing_stories, task_breakdown, total_points | Jira Stories + Estimation |

```python
# app/services/context_assembler.py
class ContextAssembler:
    async def assemble_agent_context(
        self,
        agent_name: str,
        loaded_projects: Dict[str, ProjectDocuments],
        current_requirement: str,
    ) -> Dict[str, Any]:
        """Returns agent-optimized context from loaded documents."""
        context = {
            "current_requirement": current_requirement,
            "similar_projects": []
        }
        for project_id, docs in loaded_projects.items():
            relevant_data = self._get_agent_specific_data(agent_name, docs)
            context["similar_projects"].append({
                "project_id": project_id,
                "project_name": docs.tdd.project_name,
                "relevant_data": relevant_data
            })
        return context
```

---

### SSE Streaming

The system supports Server-Sent Events for real-time progress updates during pipeline execution.

#### Streaming Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SSE Streaming Architecture                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Frontend                              Backend                       │
│  ┌──────────────┐                     ┌──────────────────────────┐  │
│  │              │  POST /impact/      │                          │  │
│  │  EventSource │  run-pipeline/stream│   LangGraph Workflow     │  │
│  │              │ ─────────────────►  │                          │  │
│  │              │                     │   Agent 1 → Agent 2 ...  │  │
│  │              │  event: pipeline_   │        │                 │  │
│  │              │  start              │        │ yield event    │  │
│  │              │ ◄─────────────────  │        ▼                 │  │
│  │              │                     │   SSE Generator          │  │
│  │              │  event: agent_      │                          │  │
│  │              │  complete           │                          │  │
│  │              │ ◄─────────────────  │                          │  │
│  │              │                     │                          │  │
│  │              │  event: pipeline_   │                          │  │
│  │              │  complete           │                          │  │
│  │              │ ◄─────────────────  │                          │  │
│  └──────────────┘                     └──────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### Event Types

| Event | Description | Payload |
|-------|-------------|---------|
| `pipeline_start` | Pipeline execution begins | `{session_id, total_agents}` |
| `agent_complete` | Agent finished processing | `{agent_name, agent_index, progress_percent, output}` |
| `pipeline_complete` | All agents finished | `{session_id, status, final_output}` |
| `pipeline_error` | Error occurred | `{session_id, error_message}` |

#### Event Format

```python
class StreamEvent(BaseModel):
    type: Literal["pipeline_start", "agent_complete", "pipeline_complete", "pipeline_error"]
    session_id: str
    timestamp: str
    data: StreamEventData

class StreamEventData(BaseModel):
    agent_name: str | None = None
    agent_index: int | None = None
    total_agents: int = 7
    status: str | None = None
    output: Dict | None = None
    progress_percent: int | None = None
```

---

### Configuration Management

#### Settings Class

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Centralized configuration."""

    # Loads from environment variables and .env file
    ollama_base_url: str = "http://localhost:11434"
    ollama_gen_model: str = "phi3:mini"
    search_semantic_weight: float = 0.70

    class Config:
        env_file = ".env"
        env_prefix = ""  # No prefix


@lru_cache()
def get_settings() -> Settings:
    """Singleton settings instance (cached)."""
    return Settings()
```

**Benefits:**
- Type-safe configuration
- Environment variable overrides
- Validation on startup
- Singleton pattern via `@lru_cache`

#### Configuration Hierarchy

```
1. Default values (in Settings class)
2. config/settings.yaml (if exists)
3. .env file
4. Environment variables (highest priority)
```

Example override:
```bash
# .env file
OLLAMA_GEN_MODEL=llama3
SEARCH_SEMANTIC_WEIGHT=0.8

# Or export
export OLLAMA_GEN_MODEL=llama3
```

---

### Error Handling

#### Exception Hierarchy

```python
# Base exception
class ComponentError(Exception):
    """Base for all component errors."""

    def __init__(self, message: str, component: str, details: Dict = None):
        self.message = message
        self.component = component
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for API response."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "component": self.component,
            "details": self.details,
        }


# Specific exceptions
class OllamaUnavailableError(ComponentError):
    """Ollama service not reachable."""
    pass


class ResponseParsingError(ComponentError):
    """Failed to parse LLM JSON response."""
    pass


class NoMatchesFoundError(ComponentError):
    """Search returned no results."""
    pass
```

#### Error Flow

```
┌────────────────────────────────────────────────────────┐
│              Error Handling Flow                        │
├────────────────────────────────────────────────────────┤
│                                                         │
│  Service raises ComponentError                         │
│           │                                             │
│           ▼                                             │
│  Router catches exception                              │
│           │                                             │
│           ▼                                             │
│  Convert to HTTPException                              │
│  status_code=400, detail=error.to_dict()               │
│           │                                             │
│           ▼                                             │
│  FastAPI returns JSON error response                   │
│  {                                                      │
│    "error": "ResponseParsingError",                    │
│    "message": "Failed to parse...",                    │
│    "component": "tdd",                                 │
│    "details": {...}                                    │
│  }                                                      │
│                                                         │
└────────────────────────────────────────────────────────┘
```

#### Best Practices

```python
# ✅ Good: Specific exception with context
raise ResponseParsingError(
    message="Failed to parse TDD response",
    component="tdd",
    details={
        "raw_response": raw[:500],
        "parse_error": str(e),
    }
)

# ❌ Bad: Generic exception
raise Exception("Parsing failed")
```

---

## Data Flow

### End-to-End Request Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Complete Request Flow                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. HTTP POST /api/v1/orchestrator/run                             │
│     Body: {"session_id": "...", "requirement_text": "..."}         │
│                    │                                                 │
│                    ▼                                                 │
│  2. FastAPI Router (orchestrator/router.py)                        │
│     • Pydantic validates request                                    │
│     • Extract session_id, requirement_text                          │
│                    │                                                 │
│                    ▼                                                 │
│  3. Initialize State                                                │
│     {                                                                │
│       "session_id": "sess_123",                                     │
│       "requirement_text": "Build auth system...",                   │
│       "status": "created",                                          │
│       "messages": []                                                │
│     }                                                                │
│                    │                                                 │
│                    ▼                                                 │
│  4. Execute LangGraph Workflow                                      │
│     workflow.ainvoke(initial_state)                                 │
│                    │                                                 │
│     ┌──────────────┴──────────────┐                                │
│     │                               │                                │
│     ▼                               ▼                                │
│  [requirement_agent]          [Audit Trail]                         │
│     • Extract keywords         • Save requirement.json              │
│     • Returns:                 • Save keywords.json                 │
│       - extracted_keywords                                           │
│       - status: "requirement_submitted"                             │
│       - current_agent: "search"                                     │
│                    │                                                 │
│                    ▼                                                 │
│  [search_agent]                                                     │
│     • Query: requirement_text                                       │
│     • HybridSearch:                                                 │
│       ├─ Semantic (ChromaDB)                                        │
│       ├─ Keyword (BM25)                                             │
│       └─ Fusion (70/30)                                             │
│     • Returns:                                                       │
│       - all_matches [...]                                           │
│       - status: "matches_found"                                     │
│       - current_agent: "auto_select"                                │
│                    │                                                 │
│                    ▼                                                 │
│  [auto_select_agent]                                                │
│     • Filter top matches                                            │
│     • Returns:                                                       │
│       - selected_matches [...]                                      │
│       - current_agent: "impacted_modules"                           │
│                    │                                                 │
│                    ▼                                                 │
│  [impacted_modules_agent]                                           │
│     • LLM prompt with requirement + matches                         │
│     • Ollama generates JSON                                         │
│     • Parse response (json_repair.py)                               │
│     • Returns:                                                       │
│       - impacted_modules_output {...}                               │
│       - current_agent: "estimation_effort"                          │
│                    │                                                 │
│                    ▼                                                 │
│  [estimation_effort_agent]                                          │
│     • LLM estimates effort                                          │
│     • Returns:                                                       │
│       - estimation_effort_output {...}                              │
│       - current_agent: "tdd"                                        │
│                    │                                                 │
│                    ▼                                                 │
│  [tdd_agent]                                                        │
│     • LLM generates TDD                                             │
│     • Returns:                                                       │
│       - tdd_output {...}                                            │
│       - current_agent: "jira_stories"                               │
│                    │                                                 │
│                    ▼                                                 │
│  [jira_stories_agent]                                               │
│     • LLM generates stories + tasks                                 │
│     • Returns:                                                       │
│       - jira_stories_output {...}                                   │
│       - status: "completed"                                         │
│       - current_agent: "END"                                        │
│                    │                                                 │
│                    ▼                                                 │
│  5. Workflow Complete                                               │
│     final_state = {...}  # All outputs accumulated                 │
│                    │                                                 │
│                    ▼                                                 │
│  6. Save Final Summary                                              │
│     AuditTrailManager.save("final_summary.json")                    │
│                    │                                                 │
│                    ▼                                                 │
│  7. HTTP Response 200 OK                                            │
│     {                                                                │
│       "session_id": "sess_123",                                     │
│       "status": "completed",                                        │
│       "impacted_modules": {...},                                    │
│       "estimation_effort": {...},                                   │
│       "tdd": {...},                                                 │
│       "jira_stories": {...}                                         │
│     }                                                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Cross-Cutting Concerns

### Logging

```python
import structlog

logger = structlog.get_logger(component="my_component")

# Structured logging
logger.info(
    "processing_request",
    session_id=session_id,
    requirement_length=len(requirement_text),
)

# Output (development):
# 2024-01-15T10:30:45 [info] processing_request session_id=sess_123 requirement_length=156

# Output (production JSON):
# {"timestamp": "2024-01-15T10:30:45", "level": "info", "component": "my_component", "event": "processing_request", "session_id": "sess_123"}
```

### Audit Trails

```python
from app.utils.audit import AuditTrailManager

audit = AuditTrailManager(session_id="sess_123")

# Save JSON
audit.save_json("output.json", data, subfolder="step3_agents/agent_tdd")

# Save text
audit.save_text("prompt.txt", prompt_text, subfolder="step3_agents/agent_tdd")

# Record timing
audit.record_timing("tdd_generation", elapsed_ms=12500)

# Add completion marker
audit.add_step_completed("tdd_generated")
```

**Directory structure:**
```
sessions/2024-01-15/sess_123/
├── step1_input/
├── step2_search/
├── step3_agents/
│   └── agent_tdd/
│       ├── input_prompt.txt
│       ├── raw_response.txt
│       └── parsed_output.json
└── final_summary.json
```

### Testing

```python
# Unit test
@pytest.mark.asyncio
async def test_component():
    service = MyService()
    request = MyRequest(...)
    response = await service.process(request)
    assert response.field == expected_value


# Integration test
async def test_workflow():
    initial_state = {...}
    result = await workflow.ainvoke(initial_state)
    assert result["status"] == "completed"


# API test
def test_endpoint(client: TestClient):
    response = client.post("/api/v1/endpoint", json={...})
    assert response.status_code == 200
```

---

## Architecture Decisions

### Why LangGraph?

**Alternatives considered:**
- LangChain (LCEL)
- Custom orchestration
- Airflow/Prefect

**Why LangGraph wins:**
- **Stateful workflows:** Explicit state management
- **Conditional routing:** Easy branching logic
- **Async native:** Built for async Python
- **Debuggable:** Clear execution graph
- **LangChain compatible:** Can use LangChain tools

### Why ChromaDB?

**Alternatives:**
- FAISS (standalone)
- Pinecone (cloud)
- Weaviate (self-hosted)

**Why ChromaDB:**
- **Embedded mode:** No separate server needed
- **Persistent storage:** Survives restarts
- **Simple API:** Easy to use
- **Metadata filtering:** Rich query capabilities
- **Open source:** Self-hosted, free

### Why Ollama?

**Alternatives:**
- OpenAI API
- Anthropic Claude API
- HuggingFace Inference

**Why Ollama:**
- **Local execution:** No API costs, data privacy
- **Fast iteration:** No network latency
- **Model flexibility:** Easy to swap models
- **Offline capable:** Works without internet
- **Cost:** Zero per-request cost

### Why Component Pattern?

**Benefits:**
- **Modularity:** Components are independent
- **Testability:** Easy to test in isolation
- **Reusability:** Components used in REST + workflow
- **Consistency:** Same structure everywhere
- **Documentation:** README per component

---

## Scalability & Performance

### Current Performance

| Operation | Time | Bottleneck |
|-----------|------|------------|
| Keyword extraction | ~10ms | CPU (regex) |
| Semantic search | ~200ms | Embedding generation |
| LLM generation (per agent) | ~5-15s | Ollama inference |
| Full pipeline (7 agents) | ~60-90s | Sequential LLM calls |

### Optimization Strategies

1. **Parallel agent execution** (if dependencies allow):
   ```python
   # Run independent agents concurrently
   results = await asyncio.gather(
       module_agent(state),
       risk_agent(state),
   )
   ```

2. **Smaller LLM models:**
   ```bash
   # phi3:mini (2.3GB) vs llama3 (4.7GB)
   # 3x faster, 80% accuracy trade-off
   export OLLAMA_GEN_MODEL=phi3:mini
   ```

3. **Cache embeddings:**
   ```python
   # Cache common queries
   @lru_cache(maxsize=1000)
   def get_embedding(text: str) -> List[float]:
       return embedding_service.embed_query(text)
   ```

4. **Limit search results:**
   ```bash
   export SEARCH_MAX_RESULTS=10  # Default: 10
   ```

### Scaling Horizontally

```
┌────────────────────────────────────────┐
│         Load Balancer (nginx)          │
└────────┬───────────────────┬───────────┘
         │                   │
    ┌────▼────┐         ┌────▼────┐
    │ API     │         │ API     │
    │ Server  │         │ Server  │
    │ (uvicorn)         │ (uvicorn)
    └────┬────┘         └────┬────┘
         │                   │
         └────────┬──────────┘
                  │
         ┌────────▼────────┐
         │   Shared State  │
         ├─────────────────┤
         │ • ChromaDB      │
         │ • Ollama        │
         │ • File storage  │
         └─────────────────┘
```

**Challenges:**
- ChromaDB in embedded mode (single instance)
- Ollama inference (GPU-bound, hard to parallelize)
- Session audit trails (file I/O)

**Solutions:**
- Use ChromaDB server mode
- Dedicated Ollama server(s) with load balancing
- Shared filesystem (NFS) or object storage (S3)

---

## See Also

- [README.md](../README.md) - Quick start guide
- [HOW_TO_GUIDE.md](HOW_TO_GUIDE.md) - Development recipes
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Debug workflows
- [Component READMEs](../app/components/) - Component details
