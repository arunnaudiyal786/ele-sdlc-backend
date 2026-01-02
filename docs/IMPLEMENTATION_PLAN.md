# AI Impact Assessment System - Backend Implementation Plan

## Executive Summary

This document outlines the implementation plan for the AI Impact Assessment System backend using the **Component-as-a-Service** architecture pattern. Each functional domain is a self-contained component with its own agent, service, models, tools, and router—enabling modularity, testability, and clear separation of concerns.

**Key Architecture Principle**: Each component owns its complete vertical slice (HTTP → Service → Agent → LLM), making it independently deployable and testable.

---

## 1. Implementation Phases Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│              IMPLEMENTATION PHASES (Component-Based)                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Phase 1: Foundation (Base Component Infrastructure)                     │
│  ├── components/base/ (abstract base, config, exceptions)               │
│  ├── Shared RAG pipeline (embeddings, vector_store, hybrid_search)      │
│  ├── Shared utilities (audit, helpers, logging)                         │
│  └── FastAPI app skeleton with lifespan management                      │
│                                                                          │
│  Phase 2: Session Component                                              │
│  ├── components/session/ (service, models, router)                      │
│  └── Session lifecycle + audit trail management                         │
│                                                                          │
│  Phase 3: Requirement Component (Step 1)                                 │
│  ├── components/requirement/ (agent, service, models, router)           │
│  └── Input validation + keyword extraction + file uploads               │
│                                                                          │
│  Phase 4: Search Component (Step 2)                                      │
│  ├── components/search/ (agent, tools, service, models, router)         │
│  └── Hybrid search orchestration (70% semantic + 30% keyword)           │
│                                                                          │
│  Phase 5: LLM Agent Components (Step 3)                                  │
│  ├── components/modules/   (identify 10 impacted modules)               │
│  ├── components/effort/    (dev/QA hours breakdown)                     │
│  ├── components/stories/   (generate 10 Jira stories)                   │
│  ├── components/code_impact/ (8-12 impacted files)                      │
│  └── components/risks/     (5 risks with mitigations)                   │
│                                                                          │
│  Phase 6: Orchestrator & Integration                                     │
│  ├── components/orchestrator/ (LangGraph workflow, state, router)       │
│  ├── Sequential agent execution with routing                            │
│  ├── Wire all component routers into main app                           │
│  └── Scripts (init_vector_db, reindex)                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Target Folder Structure (Component-as-a-Service)

```
ai-impact-assessment/
│
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI entry point + router assembly
│   │
│   ├── components/                      # Self-contained domain components
│   │   │
│   │   ├── base/                        # Shared base infrastructure
│   │   │   ├── __init__.py
│   │   │   ├── component.py             # Abstract BaseComponent[TReq, TRes]
│   │   │   ├── config.py                # Pydantic Settings + centralized config
│   │   │   ├── exceptions.py            # Exception hierarchy
│   │   │   └── logging.py               # Structured logging setup
│   │   │
│   │   ├── session/                     # Session management component
│   │   │   ├── __init__.py
│   │   │   ├── service.py               # SessionService (BaseComponent)
│   │   │   ├── models.py                # SessionRequest, SessionResponse
│   │   │   └── router.py                # POST /session/create, GET /session/{id}
│   │   │
│   │   ├── requirement/                 # Step 1: Input requirement component
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                 # requirement_agent() - LangGraph node
│   │   │   ├── service.py               # RequirementService (BaseComponent)
│   │   │   ├── models.py                # RequirementRequest, RequirementResponse
│   │   │   └── router.py                # POST /requirement/submit, /upload
│   │   │
│   │   ├── search/                      # Step 2: Historical search component
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                 # search_agent() - LangGraph node
│   │   │   ├── tools.py                 # @tool search_similar_projects()
│   │   │   ├── service.py               # SearchService (BaseComponent)
│   │   │   ├── models.py                # SearchRequest, MatchResult, SearchResponse
│   │   │   └── router.py                # POST /search/find-matches, /select-matches
│   │   │
│   │   ├── modules/                     # Agent: Impacted modules component
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                 # modules_agent() - LangGraph node
│   │   │   ├── tools.py                 # @tool identify_modules()
│   │   │   ├── service.py               # ModulesService (BaseComponent)
│   │   │   ├── models.py                # ModulesRequest, ModulesResponse
│   │   │   ├── prompts.py               # MODULES_SYSTEM_PROMPT template
│   │   │   └── router.py                # POST /impact/generate/modules
│   │   │
│   │   ├── effort/                      # Agent: Effort estimation component
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                 # effort_agent() - LangGraph node
│   │   │   ├── tools.py                 # @tool estimate_effort()
│   │   │   ├── service.py               # EffortService (BaseComponent)
│   │   │   ├── models.py                # EffortRequest, EffortResponse
│   │   │   ├── prompts.py               # EFFORT_SYSTEM_PROMPT template
│   │   │   └── router.py                # POST /impact/generate/effort
│   │   │
│   │   ├── stories/                     # Agent: Jira stories component
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                 # stories_agent() - LangGraph node
│   │   │   ├── tools.py                 # @tool generate_stories()
│   │   │   ├── service.py               # StoriesService (BaseComponent)
│   │   │   ├── models.py                # StoriesRequest, StoriesResponse
│   │   │   ├── prompts.py               # STORIES_SYSTEM_PROMPT template
│   │   │   └── router.py                # POST /impact/generate/stories
│   │   │
│   │   ├── code_impact/                 # Agent: Code impact component
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                 # code_impact_agent() - LangGraph node
│   │   │   ├── tools.py                 # @tool analyze_code_impact()
│   │   │   ├── service.py               # CodeImpactService (BaseComponent)
│   │   │   ├── models.py                # CodeImpactRequest, CodeImpactResponse
│   │   │   ├── prompts.py               # CODE_IMPACT_SYSTEM_PROMPT template
│   │   │   └── router.py                # POST /impact/generate/code
│   │   │
│   │   ├── risks/                       # Agent: Risks component
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                 # risks_agent() - LangGraph node
│   │   │   ├── tools.py                 # @tool identify_risks()
│   │   │   ├── service.py               # RisksService (BaseComponent)
│   │   │   ├── models.py                # RisksRequest, RisksResponse
│   │   │   ├── prompts.py               # RISKS_SYSTEM_PROMPT template
│   │   │   └── router.py                # POST /impact/generate/risks
│   │   │
│   │   └── orchestrator/                # LangGraph workflow coordination
│   │       ├── __init__.py
│   │       ├── state.py                 # ImpactAssessmentState (TypedDict)
│   │       ├── workflow.py              # StateGraph definition + routing
│   │       ├── service.py               # OrchestratorService (full pipeline)
│   │       └── router.py                # GET /impact/{session_id}/summary
│   │
│   ├── rag/                             # Shared RAG infrastructure
│   │   ├── __init__.py
│   │   ├── embeddings.py                # OllamaEmbeddingService
│   │   ├── vector_store.py              # ChromaVectorStore
│   │   └── hybrid_search.py             # HybridSearchService
│   │
│   └── utils/                           # Shared utilities
│       ├── __init__.py
│       ├── audit.py                     # AuditTrailManager
│       ├── ollama_client.py             # OllamaClient (generation + embedding)
│       └── helpers.py                   # General utilities
│
├── config/
│   └── settings.yaml                    # YAML configuration overrides
│
├── data/
│   ├── raw/                             # Source CSV/JSON (existing)
│   │   ├── epics.csv
│   │   ├── estimations.csv
│   │   ├── tdds.csv
│   │   ├── stories_tasks.csv
│   │   └── gitlab_code.json
│   ├── chroma/                          # ChromaDB persistence
│   ├── uploads/                         # User uploaded files
│   └── sessions/                        # Session audit trails
│       └── {date}/
│           └── {session_id}/
│
├── scripts/
│   ├── init_vector_db.py                # Initialize ChromaDB with data
│   └── reindex.py                       # Reindex vector database
│
├── .env                                 # Environment variables
├── .env.example                         # Template
├── requirements.txt                     # Dependencies
├── pyproject.toml                       # Project metadata
└── README.md
```

---

## 3. Phase 1: Base Component Infrastructure

### 3.1 Abstract Base Component (`app/components/base/component.py`)

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel

TRequest = TypeVar("TRequest", bound=BaseModel)
TResponse = TypeVar("TResponse", bound=BaseModel)

class BaseComponent(ABC, Generic[TRequest, TResponse]):
    """Abstract base for all components.

    Each component implements this interface, providing:
    - component_name: Unique identifier for logging/metrics
    - process(): Main async entry point
    - health_check(): Component-level health status
    """

    @property
    @abstractmethod
    def component_name(self) -> str:
        """Unique identifier for this component."""
        pass

    @abstractmethod
    async def process(self, request: TRequest) -> TResponse:
        """Main processing entry point."""
        pass

    async def health_check(self) -> dict:
        """Check component health status."""
        return {
            "component": self.component_name,
            "status": "healthy"
        }

    async def __call__(self, request: TRequest) -> TResponse:
        """Allow component to be called directly."""
        return await self.process(request)
```

### 3.2 Centralized Configuration (`app/components/base/config.py`)

```python
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache

class Settings(BaseSettings):
    """Centralized configuration for all components."""

    # Application
    app_name: str = "AI Impact Assessment System"
    app_version: str = "1.0.0"
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_gen_model: str = "phi3:mini"
    ollama_embed_model: str = "all-minilm"
    ollama_timeout_seconds: int = 120
    ollama_temperature: float = 0.3
    ollama_max_tokens: int = 2048

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_prefix: str = "impact_assessment"

    # Search
    search_semantic_weight: float = 0.70
    search_keyword_weight: float = 0.30
    search_max_results: int = 10
    search_min_score_threshold: float = 0.3

    # Paths
    data_raw_path: str = "./data/raw"
    data_uploads_path: str = "./data/uploads"
    data_sessions_path: str = "./data/sessions"

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    """Singleton settings instance."""
    return Settings()
```

### 3.3 Exception Hierarchy (`app/components/base/exceptions.py`)

```python
from typing import Optional, Dict, Any

class ComponentError(Exception):
    """Base exception for all component errors."""

    def __init__(self, message: str, component: str = "unknown", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.component = component
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "component": self.component,
            "details": self.details
        }

# Session Component Exceptions
class SessionNotFoundError(ComponentError): pass
class InvalidSessionStateError(ComponentError): pass

# Requirement Component Exceptions
class RequirementTooShortError(ComponentError): pass
class FileTypeNotAllowedError(ComponentError): pass
class FileTooLargeError(ComponentError): pass

# Search Component Exceptions
class SearchWeightsInvalidError(ComponentError): pass
class NoMatchesFoundError(ComponentError): pass

# Agent Component Exceptions
class AgentExecutionError(ComponentError): pass
class PromptFormattingError(ComponentError): pass
class ResponseParsingError(ComponentError): pass

# External Service Exceptions
class OllamaUnavailableError(ComponentError): pass
class OllamaTimeoutError(ComponentError): pass
class VectorDBError(ComponentError): pass
```

### 3.4 Structured Logging (`app/components/base/logging.py`)

```python
import structlog
from typing import Any

def configure_logging(environment: str = "development") -> None:
    """Configure structlog for the application."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if environment == "production"
            else structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(component_name: str) -> Any:
    """Get a logger bound to a component."""
    return structlog.get_logger(component=component_name)
```

### 3.5 Workflow State (`app/components/orchestrator/state.py`)

```python
from typing import TypedDict, Annotated, List, Dict, Optional, Literal
import operator

class ImpactAssessmentState(TypedDict, total=False):
    """Workflow state for impact assessment pipeline.

    Using total=False allows nodes to return PARTIAL updates.
    LangGraph automatically merges partial returns into full state.
    """

    # ═══════════════════════════════════════════════════
    # SESSION CONTEXT - Set at workflow start
    # ═══════════════════════════════════════════════════
    session_id: str
    requirement_text: str
    jira_epic_id: Optional[str]
    extracted_keywords: List[str]

    # ═══════════════════════════════════════════════════
    # SEARCH RESULTS - Set by search component
    # ═══════════════════════════════════════════════════
    all_matches: List[Dict]
    selected_matches: List[Dict]

    # ═══════════════════════════════════════════════════
    # AGENT OUTPUTS - Set by each agent component
    # ═══════════════════════════════════════════════════
    modules_output: Dict
    effort_output: Dict
    stories_output: Dict
    code_impact_output: Dict
    risks_output: Dict

    # ═══════════════════════════════════════════════════
    # CONTROL FIELDS - Updated throughout workflow
    # ═══════════════════════════════════════════════════
    status: Literal["created", "requirement_submitted", "matches_found",
                    "matches_selected", "generating_impact", "completed", "error"]
    current_agent: str
    error_message: Optional[str]

    # ═══════════════════════════════════════════════════
    # TIMING & AUDIT
    # ═══════════════════════════════════════════════════
    timing: Dict[str, int]  # {step_name: duration_ms}

    # Accumulated messages (uses operator.add reducer)
    messages: Annotated[List[Dict], operator.add]
```

---

## 4. Phase 2: Data Layer & RAG Pipeline

### 4.1 ChromaDB Collections Schema

| Collection | Document | Key Metadata |
|------------|----------|--------------|
| `epics` | epic_title + epic_description | epic_id, status, priority, team |
| `estimations` | task_description + tdd_description | estimation_id, epic_id, dev_hours, complexity |
| `tdds` | tdd_section_name + tdd_section_content_summary | tdd_id, epic_id, tdd_section_id, technologies |
| `stories` | story_title + acceptance_criteria | story_id, epic_id, story_type, story_points |
| `gitlab_code` | code_block_description + functions_defined | code_id, story_id, repo, language |

### 4.2 Embedding Service (`app/rag/embeddings.py`)

```python
class OllamaEmbeddingService:
    """Generate embeddings using Ollama all-minilm model."""

    async def embed(self, text: str) -> List[float]:
        """Generate 384-dim embedding vector."""

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding for efficiency."""

    def preprocess(self, text: str) -> str:
        """Lowercase, remove whitespace, truncate to 512 tokens."""
```

### 4.3 Vector Store (`app/rag/vector_store.py`)

```python
class ChromaVectorStore:
    """ChromaDB operations for all collections."""

    def __init__(self, persist_dir: str):
        self.client = chromadb.PersistentClient(path=persist_dir)

    def get_or_create_collection(self, name: str) -> Collection:
        """Get or create a collection with embedding function."""

    async def add_documents(self, collection: str, documents: List[Dict]):
        """Add documents with embeddings and metadata."""

    async def search(self, collection: str, query: str, top_k: int,
                     filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """Semantic search with optional metadata filtering."""

    async def delete_collection(self, name: str):
        """Delete and recreate collection for reindexing."""
```

### 4.4 Hybrid Search (`app/rag/hybrid_search.py`)

```python
class HybridSearchService:
    """Hybrid search combining semantic + keyword matching."""

    def __init__(self, vector_store: ChromaVectorStore,
                 semantic_weight: float = 0.7,
                 keyword_weight: float = 0.3):
        self.vector_store = vector_store
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

    async def search(self, query: str, collections: List[str],
                     top_k: int = 10) -> List[Dict]:
        """
        1. Run semantic search across collections
        2. Run keyword/BM25 search
        3. Fuse scores: final = (W1 * semantic) + (W2 * keyword)
        4. Deduplicate and rank
        5. Return top_k results with score breakdown
        """

    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords for keyword matching."""

    def calculate_keyword_score(self, query_keywords: List[str],
                                 doc_text: str) -> float:
        """TF-IDF style keyword matching."""
```

---

## 5. Phase 2: Session Component

### 5.1 Session Models (`app/components/session/models.py`)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class SessionCreateRequest(BaseModel):
    """Request to create a new assessment session."""
    user_id: Optional[str] = None

class SessionResponse(BaseModel):
    """Session details response."""
    session_id: str
    created_at: datetime
    status: str
    audit_path: str
    user_id: Optional[str] = None

class SessionAuditResponse(BaseModel):
    """Full audit trail for a session."""
    session_id: str
    created_at: datetime
    status: str
    steps_completed: List[str]
    timing: Dict[str, int]
    data: Dict  # Full audit data
```

### 5.2 Session Service (`app/components/session/service.py`)

```python
from ..base.component import BaseComponent
from ..base.config import get_settings
from ..base.exceptions import SessionNotFoundError
from .models import SessionCreateRequest, SessionResponse
import secrets
from datetime import datetime
from pathlib import Path

class SessionService(BaseComponent[SessionCreateRequest, SessionResponse]):
    """Session lifecycle management as a component."""

    def __init__(self):
        self.config = get_settings()
        self.sessions_path = Path(self.config.data_sessions_path)

    @property
    def component_name(self) -> str:
        return "session"

    async def process(self, request: SessionCreateRequest) -> SessionResponse:
        """Create a new session."""
        # Generate session_id: sess_{YYYYMMDD}_{HHMMSS}_{random6}
        now = datetime.now()
        random_suffix = secrets.token_hex(3)
        session_id = f"sess_{now.strftime('%Y%m%d')}_{now.strftime('%H%M%S')}_{random_suffix}"

        # Create directory structure
        date_folder = now.strftime("%Y-%m-%d")
        session_dir = self.sessions_path / date_folder / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Initialize session_metadata.json
        metadata = {
            "session_id": session_id,
            "created_at": now.isoformat(),
            "status": "created",
            "user_id": request.user_id,
            "steps_completed": [],
            "timing": {}
        }
        self._save_metadata(session_dir, metadata)

        return SessionResponse(
            session_id=session_id,
            created_at=now,
            status="created",
            audit_path=str(session_dir),
            user_id=request.user_id
        )

    async def get_session(self, session_id: str) -> SessionResponse:
        """Retrieve session by ID."""
        session_dir = self._find_session_dir(session_id)
        if not session_dir:
            raise SessionNotFoundError(f"Session {session_id} not found", component="session")
        metadata = self._load_metadata(session_dir)
        return SessionResponse(**metadata, audit_path=str(session_dir))
```

### 5.3 Session Router (`app/components/session/router.py`)

```python
from fastapi import APIRouter, Depends, HTTPException
from .service import SessionService
from .models import SessionCreateRequest, SessionResponse, SessionAuditResponse
from ..base.exceptions import ComponentError

router = APIRouter(prefix="/session", tags=["Session"])

_service: SessionService | None = None

def get_service() -> SessionService:
    global _service
    if _service is None:
        _service = SessionService()
    return _service

@router.post("/create", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    service: SessionService = Depends(get_service)
) -> SessionResponse:
    """Create a new assessment session."""
    return await service.process(request)

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    service: SessionService = Depends(get_service)
) -> SessionResponse:
    """Get session details."""
    try:
        return await service.get_session(session_id)
    except ComponentError as e:
        raise HTTPException(status_code=404, detail=e.to_dict())

@router.get("/{session_id}/audit", response_model=SessionAuditResponse)
async def get_session_audit(
    session_id: str,
    service: SessionService = Depends(get_service)
) -> SessionAuditResponse:
    """Get full audit trail for a session."""
    return await service.get_audit(session_id)
```

### 5.4 Audit Trail Structure

```
sessions/2025-12-31/sess_20251231_143052_abc123/
├── session_metadata.json      # Session state and timing
├── step1_input/
│   ├── requirement.json       # Submitted requirement
│   ├── extracted_keywords.json
│   └── uploads/               # Uploaded documents
├── step2_search/
│   ├── search_request.json    # Search config used
│   ├── all_matches.json       # All matches returned
│   └── selected_matches.json  # User selections
├── step3_agents/
│   ├── agent_modules/
│   │   ├── input_prompt.txt   # Full prompt sent
│   │   ├── raw_response.txt   # Raw LLM response
│   │   └── parsed_output.json # Structured output
│   ├── agent_effort/
│   ├── agent_stories/
│   ├── agent_code/
│   └── agent_risks/
└── final_summary.json         # Aggregated output
```

---

## 6. Phase 3: Requirement Component (Step 1)

### 6.1 Requirement Models (`app/components/requirement/models.py`)

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class RequirementSubmitRequest(BaseModel):
    """Request to submit a requirement."""
    session_id: str
    requirement_description: str = Field(..., min_length=20)
    jira_epic_id: Optional[str] = None

class RequirementResponse(BaseModel):
    """Response after requirement submission."""
    session_id: str
    requirement_id: str
    status: str
    character_count: int
    extracted_keywords: List[str]
    created_at: datetime
```

### 6.2 Requirement Service (`app/components/requirement/service.py`)

```python
from ..base.component import BaseComponent
from ..base.exceptions import RequirementTooShortError
from .models import RequirementSubmitRequest, RequirementResponse
import re

class RequirementService(BaseComponent[RequirementSubmitRequest, RequirementResponse]):
    """Process and validate requirements."""

    @property
    def component_name(self) -> str:
        return "requirement"

    async def process(self, request: RequirementSubmitRequest) -> RequirementResponse:
        """Process submitted requirement."""
        # Validate length
        if len(request.requirement_description) < 20:
            raise RequirementTooShortError(
                "Requirement must be at least 20 characters",
                component="requirement"
            )

        # Extract keywords (simple implementation)
        keywords = self._extract_keywords(request.requirement_description)

        # Save to session audit trail
        # ...

        return RequirementResponse(
            session_id=request.session_id,
            requirement_id=f"req_{request.session_id}",
            status="submitted",
            character_count=len(request.requirement_description),
            extracted_keywords=keywords,
            created_at=datetime.now()
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from requirement text."""
        # Simple keyword extraction (can be enhanced with NLP)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        stopwords = {'that', 'this', 'with', 'from', 'have', 'will', 'should', 'would'}
        return list(set(words) - stopwords)[:20]
```

### 6.3 Requirement Agent (`app/components/requirement/agent.py`)

```python
from typing import Dict, Any
from .service import RequirementService
from .models import RequirementSubmitRequest

_service: RequirementService | None = None

def get_service() -> RequirementService:
    global _service
    if _service is None:
        _service = RequirementService()
    return _service

async def requirement_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for requirement processing.

    Returns PARTIAL state update - only changed fields.
    """
    try:
        service = get_service()

        request = RequirementSubmitRequest(
            session_id=state["session_id"],
            requirement_description=state["requirement_text"],
            jira_epic_id=state.get("jira_epic_id")
        )

        response = await service.process(request)

        # Return partial state update
        return {
            "extracted_keywords": response.extracted_keywords,
            "status": "requirement_submitted",
            "current_agent": "search",
            "messages": [{
                "role": "requirement",
                "content": f"Extracted {len(response.extracted_keywords)} keywords"
            }]
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler"
        }
```

---

## 7. Phase 4: Search Component (Step 2)

### 7.1 Search Models (`app/components/search/models.py`)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class SearchRequest(BaseModel):
    """Request to search for historical matches."""
    session_id: str
    query: str
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    max_results: int = Field(default=10, ge=1, le=50)

class MatchResult(BaseModel):
    """Single match result."""
    match_id: str
    epic_id: str
    epic_name: str
    description: str
    match_score: float
    score_breakdown: Dict[str, float]  # {semantic: 0.8, keyword: 0.6}
    technologies: List[str]
    actual_hours: Optional[int] = None
    estimated_hours: Optional[int] = None

class SearchResponse(BaseModel):
    """Search results response."""
    session_id: str
    total_matches: int
    matches: List[MatchResult]
    search_time_ms: int

class MatchSelectionRequest(BaseModel):
    """Request to select matches for impact analysis."""
    session_id: str
    selected_match_ids: List[str]
```

### 7.2 Search Service (`app/components/search/service.py`)

```python
from ..base.component import BaseComponent
from .models import SearchRequest, SearchResponse, MatchResult
from ...rag.hybrid_search import HybridSearchService

class SearchService(BaseComponent[SearchRequest, SearchResponse]):
    """Hybrid search service as a component."""

    def __init__(self, hybrid_search: HybridSearchService):
        self.hybrid_search = hybrid_search

    @property
    def component_name(self) -> str:
        return "search"

    async def process(self, request: SearchRequest) -> SearchResponse:
        """Execute hybrid search."""
        import time
        start = time.time()

        # Run hybrid search across collections
        results = await self.hybrid_search.search(
            query=request.query,
            collections=["epics", "estimations", "tdds"],
            top_k=request.max_results,
            semantic_weight=request.semantic_weight,
            keyword_weight=request.keyword_weight
        )

        # Convert to MatchResult objects
        matches = [MatchResult(**r) for r in results]

        elapsed_ms = int((time.time() - start) * 1000)

        return SearchResponse(
            session_id=request.session_id,
            total_matches=len(matches),
            matches=matches,
            search_time_ms=elapsed_ms
        )
```

### 7.3 Search Tools (`app/components/search/tools.py`)

```python
from langchain_core.tools import tool
from typing import List, Dict

@tool
def search_similar_projects(
    query: str,
    top_k: int = 10,
    semantic_weight: float = 0.7
) -> List[Dict]:
    """Search for similar historical projects.

    Args:
        query: Search query (requirement text)
        top_k: Number of results to return
        semantic_weight: Weight for semantic vs keyword search

    Returns:
        List of matching projects with scores
    """
    from .service import SearchService
    from ...rag.hybrid_search import HybridSearchService
    import asyncio

    # Get singleton instances
    hybrid_search = HybridSearchService.get_instance()
    service = SearchService(hybrid_search)

    from .models import SearchRequest
    request = SearchRequest(
        session_id="tool_call",
        query=query,
        semantic_weight=semantic_weight,
        keyword_weight=1.0 - semantic_weight,
        max_results=top_k
    )

    response = asyncio.run(service.process(request))
    return [m.model_dump() for m in response.matches]
```

---

## 8. Phase 5: LLM Agent Components

### 8.1 Example: Modules Component (`app/components/modules/`)

Each agent component follows the same pattern. Here's the Modules component as reference:

#### `models.py`
```python
from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime

class ModuleItem(BaseModel):
    """Single module in impact analysis."""
    name: str
    impact: str = Field(..., pattern="^(HIGH|MEDIUM|LOW)$")
    reason: str

class ModulesRequest(BaseModel):
    """Request to identify impacted modules."""
    session_id: str
    requirement_text: str
    selected_matches: List[Dict]

class ModulesResponse(BaseModel):
    """Response with identified modules."""
    session_id: str
    agent: str = "modules"
    functional_modules: List[ModuleItem]
    technical_modules: List[ModuleItem]
    total_modules: int
    generated_at: datetime
    audit_file: str
```

#### `prompts.py`
```python
MODULES_SYSTEM_PROMPT = """You are an expert software architect analyzing project requirements.

Given a requirement and historical similar projects, identify the impacted modules.

OUTPUT FORMAT (JSON only, no markdown):
{
  "functional_modules": [
    {"name": "string", "impact": "HIGH|MEDIUM|LOW", "reason": "string"}
  ],
  "technical_modules": [
    {"name": "string", "impact": "HIGH|MEDIUM|LOW", "reason": "string"}
  ]
}

Provide exactly 10 modules total (mix of functional and technical)."""

MODULES_USER_PROMPT = """REQUIREMENT:
{requirement_description}

SIMILAR HISTORICAL PROJECTS:
{formatted_historical_matches}

Identify the impacted modules for this requirement."""
```

#### `service.py`
```python
from ..base.component import BaseComponent
from ..base.exceptions import ResponseParsingError
from .models import ModulesRequest, ModulesResponse, ModuleItem
from .prompts import MODULES_SYSTEM_PROMPT, MODULES_USER_PROMPT
from ...utils.ollama_client import OllamaClient
import json

class ModulesService(BaseComponent[ModulesRequest, ModulesResponse]):
    """Modules identification agent as a component."""

    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client

    @property
    def component_name(self) -> str:
        return "modules"

    async def process(self, request: ModulesRequest) -> ModulesResponse:
        """Identify impacted modules using LLM."""
        # Format prompt
        formatted_matches = self._format_matches(request.selected_matches)
        user_prompt = MODULES_USER_PROMPT.format(
            requirement_description=request.requirement_text,
            formatted_historical_matches=formatted_matches
        )

        # Call Ollama
        raw_response = await self.ollama.generate(
            system_prompt=MODULES_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json"
        )

        # Parse response
        parsed = self._parse_response(raw_response)

        return ModulesResponse(
            session_id=request.session_id,
            functional_modules=parsed["functional_modules"],
            technical_modules=parsed["technical_modules"],
            total_modules=len(parsed["functional_modules"]) + len(parsed["technical_modules"]),
            generated_at=datetime.now(),
            audit_file=f"step3_agents/agent_modules/parsed_output.json"
        )

    def _parse_response(self, raw: str) -> Dict:
        """Parse LLM JSON response."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ResponseParsingError(
                f"Failed to parse LLM response: {e}",
                component="modules",
                details={"raw_response": raw[:500]}
            )
```

#### `agent.py`
```python
from typing import Dict, Any
from .service import ModulesService
from .models import ModulesRequest

async def modules_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for modules identification."""
    try:
        from ...utils.ollama_client import get_ollama_client
        service = ModulesService(get_ollama_client())

        request = ModulesRequest(
            session_id=state["session_id"],
            requirement_text=state["requirement_text"],
            selected_matches=state["selected_matches"]
        )

        response = await service.process(request)

        return {
            "modules_output": response.model_dump(),
            "status": "modules_generated",
            "current_agent": "effort",
            "messages": [{
                "role": "modules",
                "content": f"Identified {response.total_modules} impacted modules"
            }]
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler"
        }
```

#### `router.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from .service import ModulesService
from .models import ModulesRequest, ModulesResponse

router = APIRouter(prefix="/impact", tags=["Impact Analysis"])

@router.post("/generate/modules", response_model=ModulesResponse)
async def generate_modules(request: ModulesRequest) -> ModulesResponse:
    """Generate impacted modules analysis."""
    from ...utils.ollama_client import get_ollama_client
    service = ModulesService(get_ollama_client())
    return await service.process(request)
```

### 8.2 Other Agent Components (Same Pattern)

| Component | Purpose | Output |
|-----------|---------|--------|
| `effort/` | Dev/QA hours estimation | `{dev_hours, qa_hours, story_points, confidence}` |
| `stories/` | Generate 10 Jira stories | `{stories: [{title, type, points, criteria}]}` |
| `code_impact/` | Identify 8-12 files | `{files: [{path, repo, change_type, reason}]}` |
| `risks/` | Identify 5 risks | `{risks: [{title, severity, mitigation}]}` |

---

## 9. Phase 6: Orchestrator & Integration

### 9.1 LangGraph Workflow (`app/components/orchestrator/workflow.py`)

```python
from langgraph.graph import StateGraph, END
from .state import ImpactAssessmentState
from ..requirement.agent import requirement_agent
from ..search.agent import search_agent
from ..modules.agent import modules_agent
from ..effort.agent import effort_agent
from ..stories.agent import stories_agent
from ..code_impact.agent import code_impact_agent
from ..risks.agent import risks_agent

def route_after_search(state: ImpactAssessmentState) -> str:
    """Route based on search results."""
    if state.get("status") == "error":
        return "error_handler"
    if not state.get("selected_matches"):
        return END  # No matches selected, can't proceed
    return "modules"

def route_after_agent(state: ImpactAssessmentState) -> str:
    """Generic routing after agent execution."""
    if state.get("status") == "error":
        return "error_handler"
    return state.get("current_agent", END)

def create_impact_workflow() -> StateGraph:
    """Create the LangGraph workflow for impact assessment."""
    workflow = StateGraph(ImpactAssessmentState)

    # Add nodes
    workflow.add_node("requirement", requirement_agent)
    workflow.add_node("search", search_agent)
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
    workflow.add_conditional_edges("search", route_after_search,
        {"modules": "modules", "error_handler": "error_handler", END: END})
    workflow.add_edge("modules", "effort")
    workflow.add_edge("effort", "stories")
    workflow.add_edge("stories", "code_impact")
    workflow.add_edge("code_impact", "risks")
    workflow.add_edge("risks", END)
    workflow.add_edge("error_handler", END)

    return workflow.compile()
```

### 9.2 FastAPI Main Application (`app/main.py`)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .components.base.config import get_settings
from .components.base.logging import configure_logging
from .components.session.router import router as session_router
from .components.requirement.router import router as requirement_router
from .components.search.router import router as search_router
from .components.modules.router import router as modules_router
from .components.effort.router import router as effort_router
from .components.stories.router import router as stories_router
from .components.code_impact.router import router as code_router
from .components.risks.router import router as risks_router
from .components.orchestrator.router import router as orchestrator_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    settings = get_settings()
    configure_logging(settings.environment)

    # Initialize ChromaDB connection
    from .rag.vector_store import ChromaVectorStore
    ChromaVectorStore.initialize(settings.chroma_persist_dir)

    # Verify Ollama connection
    from .utils.ollama_client import OllamaClient
    await OllamaClient.verify_connection()

    yield

    # Cleanup on shutdown
    pass

app = FastAPI(
    title="AI Impact Assessment API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount component routers
app.include_router(session_router, prefix="/api/v1")
app.include_router(requirement_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(modules_router, prefix="/api/v1")
app.include_router(effort_router, prefix="/api/v1")
app.include_router(stories_router, prefix="/api/v1")
app.include_router(code_router, prefix="/api/v1")
app.include_router(risks_router, prefix="/api/v1")
app.include_router(orchestrator_router, prefix="/api/v1")

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}
```

---

## 10. Dependencies (`requirements.txt`)

```txt
# Framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# AI/ML
chromadb>=0.4.22
ollama>=0.1.0
langgraph>=0.0.40

# Data Processing
pandas>=2.1.0
python-multipart>=0.0.6
aiofiles>=23.2.0

# HTTP Client
httpx>=0.26.0

# Configuration
python-dotenv>=1.0.0
pyyaml>=6.0.1

# Logging
structlog>=24.1.0
```

---

## 11. Environment Variables (`.env`)

```bash
# Application
APP_ENV=development
DEBUG=true

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_GEN_MODEL=phi3:mini
OLLAMA_EMBED_MODEL=all-minilm
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_TEMPERATURE=0.3

# ChromaDB
CHROMA_PERSIST_DIR=./data/chroma

# Search Weights
SEARCH_SEMANTIC_WEIGHT=0.70
SEARCH_KEYWORD_WEIGHT=0.30
SEARCH_MAX_RESULTS=10

# Paths
DATA_RAW_PATH=./data/raw
DATA_UPLOADS_PATH=./data/uploads
DATA_SESSIONS_PATH=./data/sessions

# Server
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## 12. Implementation Order (Component-Based)

### Batch 1: Base Infrastructure
1. `app/components/base/component.py` - Abstract BaseComponent
2. `app/components/base/config.py` - Settings
3. `app/components/base/exceptions.py` - Exception hierarchy
4. `app/components/base/logging.py` - Structured logging

### Batch 2: Shared Utilities
5. `app/utils/ollama_client.py` - Ollama API wrapper
6. `app/utils/audit.py` - Audit trail manager
7. `app/rag/embeddings.py` - Embedding service
8. `app/rag/vector_store.py` - ChromaDB operations
9. `app/rag/hybrid_search.py` - Hybrid search

### Batch 3: Session Component
10. `app/components/session/models.py`
11. `app/components/session/service.py`
12. `app/components/session/router.py`

### Batch 4: Requirement Component
13. `app/components/requirement/models.py`
14. `app/components/requirement/service.py`
15. `app/components/requirement/agent.py`
16. `app/components/requirement/router.py`

### Batch 5: Search Component
17. `app/components/search/models.py`
18. `app/components/search/service.py`
19. `app/components/search/tools.py`
20. `app/components/search/agent.py`
21. `app/components/search/router.py`

### Batch 6: Agent Components (5 parallel)
22-26. `app/components/modules/` (all files)
27-31. `app/components/effort/` (all files)
32-36. `app/components/stories/` (all files)
37-41. `app/components/code_impact/` (all files)
42-46. `app/components/risks/` (all files)

### Batch 7: Orchestrator & Main
47. `app/components/orchestrator/state.py`
48. `app/components/orchestrator/workflow.py`
49. `app/components/orchestrator/service.py`
50. `app/components/orchestrator/router.py`
51. `app/main.py` - FastAPI assembly

### Batch 8: Scripts
52. `scripts/init_vector_db.py`
53. `scripts/reindex.py`

---

## 13. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | Component-as-a-Service | Each domain is self-contained with agent + service + router |
| LLM Runtime | Ollama (local) | Privacy, no API costs, offline capability |
| LLM Model | phi3:mini | Lightweight, good JSON output |
| Embedding | all-minilm (384-dim) | Fast, sufficient for POC scale |
| Vector DB | ChromaDB | Lightweight, local-first, good for POC |
| Search | Hybrid (70/30) | Best of semantic + keyword |
| Workflow | LangGraph StateGraph | Native state management, conditional routing |
| Session Storage | Local filesystem | Simple, auditable, no DB setup |

---

## 14. Success Criteria

- [ ] All 20 API endpoints functional
- [ ] ChromaDB initialized with 5 collections
- [ ] Hybrid search returns relevant matches
- [ ] 5 agent components produce valid JSON output
- [ ] Session audit trail complete
- [ ] Health check passes
- [ ] Reindex script works

---

## Appendix: API Endpoint Summary

```
Session Management
  POST /api/v1/session/create
  GET  /api/v1/session/{session_id}
  GET  /api/v1/session/{session_id}/audit

Step 1: Input Requirement
  POST /api/v1/requirement/submit
  POST /api/v1/requirement/upload
  GET  /api/v1/requirement/{session_id}

Step 2: Historical Matches
  POST /api/v1/search/find-matches
  POST /api/v1/search/select-matches
  GET  /api/v1/search/{session_id}/matches

Step 3: Impact Results
  POST /api/v1/impact/generate/modules
  POST /api/v1/impact/generate/effort
  POST /api/v1/impact/generate/stories
  POST /api/v1/impact/generate/code
  POST /api/v1/impact/generate/risks
  GET  /api/v1/impact/{session_id}/summary

Configuration
  GET  /api/v1/config
  PUT  /api/v1/config/search-weights

Health & Admin
  GET  /api/v1/health
  POST /api/v1/admin/reindex
```

---

*Document Version: 2.0 (Component-Based Architecture)*
*Last Updated: December 31, 2025*
