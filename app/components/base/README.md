# Base Component

The **base** component provides foundational infrastructure for all other components in the SDLC Impact Assessment system. It establishes shared patterns, configuration management, logging, and exception handling.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     BASE COMPONENT                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐   ┌──────────────────┐                    │
│  │  BaseComponent   │   │     Settings     │                    │
│  │  (ABC + Generic) │   │  (pydantic)      │                    │
│  └────────┬─────────┘   └────────┬─────────┘                    │
│           │                      │                               │
│           │ extends              │ @lru_cache                    │
│           ▼                      ▼                               │
│  ┌──────────────────┐   ┌──────────────────┐                    │
│  │ SessionService   │   │  get_settings()  │                    │
│  │ SearchService    │   │   (Singleton)    │                    │
│  │ ModulesService   │   └──────────────────┘                    │
│  │ EffortService    │                                           │
│  │ StoriesService   │   ┌──────────────────┐                    │
│  │ CodeImpactSvc    │   │  ComponentError  │                    │
│  │ RisksService     │   │   (Exceptions)   │                    │
│  └──────────────────┘   └──────────────────┘                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
base/
├── __init__.py      # Public exports
├── component.py     # Abstract base class for all components
├── config.py        # Centralized settings management
├── logging.py       # Structured logging configuration
├── exceptions.py    # Custom exception hierarchy
└── README.md        # This file
```

## Code Walkthrough

### 1. BaseComponent (`component.py`)

This is the **abstract base class** that all service components must implement. It uses Python's generics to enforce type safety.

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
        """Unique identifier for this component."""
        pass

    @abstractmethod
    async def process(self, request: TRequest) -> TResponse:
        """Main processing entry point."""
        pass

    async def health_check(self) -> dict:
        """Check component health status."""
        return {"component": self.component_name, "status": "healthy"}

    async def __call__(self, request: TRequest) -> TResponse:
        """Allow component to be called directly."""
        return await self.process(request)
```

**Key Design Decisions:**

| Pattern | Purpose |
|---------|---------|
| `ABC` (Abstract Base Class) | Enforces subclasses implement required methods |
| `Generic[TRequest, TResponse]` | Type-safe request/response contracts |
| `@abstractmethod` | Compilation-time enforcement of interface |
| `__call__` | Allows `service(request)` syntax sugar |

**Example Implementation:**

```python
class SessionService(BaseComponent[SessionCreateRequest, SessionResponse]):
    @property
    def component_name(self) -> str:
        return "session"

    async def process(self, request: SessionCreateRequest) -> SessionResponse:
        # Implementation here
        pass
```

---

### 2. Settings (`config.py`)

Centralized configuration using Pydantic Settings with environment variable support.

```python
from pydantic_settings import BaseSettings
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

    # Ollama (LLM)
    ollama_base_url: str = "http://localhost:11434"
    ollama_gen_model: str = "phi3:mini"
    ollama_embed_model: str = "all-minilm"
    ollama_timeout_seconds: int = 120
    ollama_temperature: float = 0.3

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_prefix: str = "impact_assessment"

    # Search tuning
    search_semantic_weight: float = 0.70
    search_keyword_weight: float = 0.30
    search_max_results: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    """Singleton settings instance."""
    return Settings()
```

**Configuration Categories:**

| Category | Variables | Purpose |
|----------|-----------|---------|
| Application | `app_name`, `environment` | App metadata |
| Server | `host`, `port`, `cors_origins` | FastAPI config |
| Ollama | `ollama_*` | LLM connection |
| ChromaDB | `chroma_*` | Vector database |
| Search | `search_*` | Hybrid search tuning |
| Paths | `data_*` | File storage locations |

**Environment Override Example:**

```bash
# .env file
OLLAMA_BASE_URL=http://llm-server:11434
OLLAMA_GEN_MODEL=llama3
ENVIRONMENT=production
SEARCH_SEMANTIC_WEIGHT=0.8
```

---

### 3. Logging (`logging.py`)

Structured logging using `structlog` with environment-aware rendering.

```python
import structlog

def configure_logging(environment: str = "development") -> None:
    """Configure structlog for the application."""
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Environment-aware rendering
    if environment == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def get_logger(component_name: str):
    """Get a logger bound to a component."""
    return structlog.get_logger(component=component_name)
```

**Output Formats:**

```
# Development (Console)
2024-01-15T10:30:45 [info] Processing request  component=search session_id=sess_123

# Production (JSON)
{"timestamp": "2024-01-15T10:30:45", "level": "info", "component": "search", "event": "Processing request"}
```

---

### 4. Exceptions (`exceptions.py`)

Hierarchical exception system with rich error context.

```python
class ComponentError(Exception):
    """Base exception for all component errors."""

    def __init__(
        self,
        message: str,
        component: str = "unknown",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.component = component
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "component": self.component,
            "details": self.details,
        }
```

**Exception Hierarchy:**

```
ComponentError (Base)
├── Session Exceptions
│   ├── SessionNotFoundError
│   └── InvalidSessionStateError
├── Requirement Exceptions
│   ├── RequirementTooShortError
│   ├── FileTypeNotAllowedError
│   └── FileTooLargeError
├── Search Exceptions
│   ├── SearchWeightsInvalidError
│   └── NoMatchesFoundError
├── Agent Exceptions
│   ├── AgentExecutionError
│   ├── PromptFormattingError
│   └── ResponseParsingError
└── External Service Exceptions
    ├── OllamaUnavailableError
    ├── OllamaTimeoutError
    └── VectorDBError
```

**Usage in Routers:**

```python
from app.components.base.exceptions import ComponentError

@router.post("/submit")
async def submit(request: Request):
    try:
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
```

---

## API Reference

### BaseComponent Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `component_name` | `@property -> str` | Unique component identifier |
| `process` | `async (TRequest) -> TResponse` | Main processing logic |
| `health_check` | `async () -> dict` | Health status check |
| `__call__` | `async (TRequest) -> TResponse` | Callable shorthand |

### Settings Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `ollama_base_url` | `str` | `http://localhost:11434` | Ollama server URL |
| `ollama_gen_model` | `str` | `phi3:mini` | Generation model |
| `ollama_temperature` | `float` | `0.3` | LLM temperature |
| `search_semantic_weight` | `float` | `0.70` | Semantic search weight |
| `chroma_persist_dir` | `str` | `./data/chroma` | Vector DB path |

---

## Examples

### Creating a New Component

```python
from app.components.base import BaseComponent
from pydantic import BaseModel

class MyRequest(BaseModel):
    session_id: str
    data: str

class MyResponse(BaseModel):
    result: str
    processed: bool

class MyService(BaseComponent[MyRequest, MyResponse]):
    @property
    def component_name(self) -> str:
        return "my_service"

    async def process(self, request: MyRequest) -> MyResponse:
        # Your business logic here
        return MyResponse(result=request.data.upper(), processed=True)
```

### Using Settings

```python
from app.components.base import get_settings

settings = get_settings()
print(f"Using model: {settings.ollama_gen_model}")
print(f"Search weight: {settings.search_semantic_weight}")
```

### Raising Component Errors

```python
from app.components.base.exceptions import ResponseParsingError

def parse_llm_response(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ResponseParsingError(
            message=f"Failed to parse LLM response: {e}",
            component="modules",
            details={"raw_response": raw[:500]}
        )
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `Settings validation error` | Missing required env var | Check `.env` file |
| `ComponentError not caught` | Wrong exception type | Catch `ComponentError` base class |
| `Logging not working` | `configure_logging()` not called | Call in `main.py` startup |
| `Singleton returning stale config` | `@lru_cache` caching | Restart app or clear cache |

---

## Best Practices

1. **Always extend `BaseComponent`** - Ensures consistent interface
2. **Use `get_settings()` singleton** - Avoid creating multiple Settings instances
3. **Raise specific exceptions** - Use `SessionNotFoundError` instead of generic `ComponentError`
4. **Include `details` in errors** - Helps with debugging
5. **Log with component context** - Use `get_logger(self.component_name)`
