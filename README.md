# AI Impact Assessment System - Backend

AI-powered software impact assessment using LangGraph multi-agent orchestration, hybrid vector search, and local LLMs. Takes requirement descriptions, finds historical matches, and generates comprehensive impact analysis including effort estimates, Technical Design Documents (TDDs), Jira stories, module impacts, and risk assessments.

## Quick Start (5 Minutes)

```bash
# 1. Clone and navigate
cd ele-sdlc-backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install and start Ollama (if not already running)
# Visit: https://ollama.ai/download
ollama pull phi3:mini      # Generation model (~2.3GB)
ollama pull all-minilm     # Embeddings model (~46MB)

# 4. Initialize vector database
python scripts/init_vector_db.py

# 5. Start the server
./start_dev.sh
# Or manually: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 6. Verify it's running
curl http://localhost:8000/api/v1/health
```

**First API call:**
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"created_by": "developer"}'
```

Access the interactive API docs at: http://localhost:8000/docs

---

## What It Does

**Input:** Software requirement description
**Output:** Complete impact assessment with effort estimates, technical design, Jira stories, affected modules, and risk analysis

**How:** Multi-agent LangGraph pipeline with hybrid semantic + keyword search against historical project data.

---

## Architecture at a Glance

```
┌────────────────────────────────────────────────────────────┐
│                   LangGraph Workflow                        │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  requirement → historical_match → auto_select              │
│      ↓                                                      │
│  impacted_modules → estimation_effort → tdd → jira_stories │
│      ↓                                                      │
│  completed                                                  │
│                                                             │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│                    Tech Stack                               │
├────────────────────────────────────────────────────────────┤
│  • FastAPI - Async REST API framework                      │
│  • LangGraph - Multi-agent workflow orchestration          │
│  • ChromaDB - Vector similarity search                     │
│  • Ollama - Local LLM inference (phi3:mini)                │
│  • Pydantic - Type-safe data validation                    │
└────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
ele-sdlc-backend/
├── app/
│   ├── components/              # Modular feature components
│   │   ├── base/                # Foundation: BaseComponent, Settings, Exceptions
│   │   ├── session/             # Session lifecycle management
│   │   ├── requirement/         # Requirement intake + keyword extraction
│   │   ├── historical_match/    # Hybrid search (semantic + keyword)
│   │   ├── impacted_modules/    # Module impact analysis (LLM)
│   │   ├── estimation_effort/   # Effort estimation (LLM)
│   │   ├── tdd/                 # Technical Design Document generation
│   │   ├── jira_stories/        # Jira story + task generation
│   │   └── orchestrator/        # LangGraph workflow coordinator
│   │
│   ├── rag/                     # Retrieval-Augmented Generation
│   │   ├── embeddings.py        # Ollama embeddings service
│   │   ├── vector_store.py      # ChromaDB wrapper
│   │   └── hybrid_search.py     # Semantic (70%) + Keyword (30%) fusion
│   │
│   ├── utils/                   # Shared utilities
│   │   ├── audit.py             # Session audit trail manager
│   │   ├── json_repair.py       # LLM JSON response parser
│   │   └── id_generator.py      # Unique ID generation
│   │
│   └── main.py                  # FastAPI application entry point
│
├── data/
│   ├── chroma/                  # ChromaDB vector indices
│   ├── raw/                     # Source CSV files (epics, estimations, tdds)
│   └── uploads/                 # Uploaded requirement files
│
├── sessions/                    # Audit trails (organized by date/session_id)
├── scripts/                     # Database initialization + utilities
├── tests/                       # Pytest test suite
├── config/                      # YAML configuration files
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md          # System design deep-dive
│   ├── HOW_TO_GUIDE.md          # Developer recipes
│   └── TROUBLESHOOTING.md       # Debug workflows
│
├── start_dev.sh                 # One-command dev environment start
├── stop_dev.sh                  # Graceful shutdown
└── requirements.txt             # Python dependencies
```

---

## Key Technologies

| Technology | Purpose | Version |
|------------|---------|---------|
| **FastAPI** | Async REST API framework | ^0.100.0 |
| **LangGraph** | Multi-agent workflow orchestration | ^0.2.0 |
| **ChromaDB** | Vector similarity search | ^0.4.0 |
| **Ollama** | Local LLM inference (phi3:mini, all-minilm) | Latest |
| **Pydantic** | Data validation + settings management | ^2.0.0 |
| **structlog** | Structured logging | ^23.0.0 |

---

## Documentation Map

| Document | Purpose | Audience |
|----------|---------|----------|
| [README.md](README.md) (this file) | Quick start + project overview | Everyone |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, patterns, data flow | Architects, Senior Devs |
| [HOW_TO_GUIDE.md](docs/HOW_TO_GUIDE.md) | Step-by-step development recipes | Developers |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues + debug workflows | Developers, DevOps |
| [CLAUDE.md](CLAUDE.md) | AI coding assistant context | Claude Code users |
| **Component READMEs:** | | |
| [base/README.md](app/components/base/README.md) | Foundation: BaseComponent, Settings | All developers |
| [requirement/README.md](app/components/requirement/README.md) | Requirement intake component | Feature developers |
| [historical_match/README.md](app/components/historical_match/README.md) | Hybrid search component | Search/ML developers |
| [tdd/README.md](app/components/tdd/README.md) | TDD generation component | Agent developers |
| [estimation_effort/README.md](app/components/estimation_effort/README.md) | Effort estimation component | Agent developers |
| [impacted_modules/README.md](app/components/impacted_modules/README.md) | Module impact component | Agent developers |
| [jira_stories/README.md](app/components/jira_stories/README.md) | Story generation component | Agent developers |

---

## Essential Commands

### Development

```bash
# Start all services (Ollama + ChromaDB + API server)
./start_dev.sh

# Start manually
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Stop all services
./stop_dev.sh

# Check service health
curl http://localhost:8000/api/v1/health
curl http://localhost:11434/api/tags  # Verify Ollama
```

### Database Operations

```bash
# Initialize vector database (first time or after schema changes)
python scripts/init_vector_db.py

# Full reindex (rebuild from raw CSV files)
python scripts/reindex.py && python scripts/init_vector_db.py

# Verify collections
python -c "from app.rag.vector_store import VectorStoreManager; \
           store = VectorStoreManager.get_instance(); \
           print(store.list_collections())"
```

### Testing

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Single test file
pytest tests/test_requirement.py

# Single test function
pytest tests/test_requirement.py::test_keyword_extraction

# With coverage
pytest --cov=app --cov-report=html

# Async tests (if needed)
pytest --asyncio-mode=auto
```

### Configuration

```bash
# View current configuration
curl http://localhost:8000/api/v1/config

# Override settings via environment variables
export OLLAMA_GEN_MODEL=llama3
export SEARCH_SEMANTIC_WEIGHT=0.8
export ENVIRONMENT=production
```

---

## API Endpoints

All endpoints are under `/api/v1/`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/config` | Current configuration |
| `POST` | `/sessions` | Create new session |
| `POST` | `/requirement/submit` | Submit requirement |
| `POST` | `/historical-match/find` | Search historical projects |
| `POST` | `/historical-match/select` | Select matches for analysis |
| `POST` | `/orchestrator/run` | Execute full pipeline |
| `POST` | `/orchestrator/run-from-file` | Pipeline from file upload |

**Interactive API Docs:** http://localhost:8000/docs
**ReDoc:** http://localhost:8000/redoc

---

## Component Pattern

Every feature follows this structure:

```
app/components/{name}/
├── models.py       # Pydantic request/response schemas
├── service.py      # Business logic (extends BaseComponent)
├── agent.py        # LangGraph node wrapper
├── router.py       # FastAPI endpoints
├── prompts.py      # LLM prompts (if applicable)
└── README.md       # Component documentation
```

**Example - Adding a new component:**

```python
# models.py
from pydantic import BaseModel

class MyRequest(BaseModel):
    session_id: str
    data: str

class MyResponse(BaseModel):
    result: str

# service.py
from app.components.base import BaseComponent

class MyService(BaseComponent[MyRequest, MyResponse]):
    @property
    def component_name(self) -> str:
        return "my_service"

    async def process(self, request: MyRequest) -> MyResponse:
        # Business logic here
        return MyResponse(result=request.data.upper())

# agent.py
async def my_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node - returns PARTIAL state updates."""
    service = get_service()
    request = MyRequest(session_id=state["session_id"], data=state["data"])
    response = await service.process(request)
    return {
        "my_output": response.model_dump(),
        "status": "my_step_done",
        "current_agent": "next_agent",
    }
```

See [HOW_TO_GUIDE.md](docs/HOW_TO_GUIDE.md) for complete walkthrough.

---

## State Management

LangGraph agents return **partial state updates**. Only changed fields are returned:

```python
# Input state (full)
{
    "session_id": "sess_123",
    "requirement_text": "Build user auth...",
    "status": "created",
    "extracted_keywords": [],
}

# Agent returns (partial)
{
    "extracted_keywords": ["user", "auth", "build"],
    "status": "requirement_submitted",
    "current_agent": "search",
}

# Result (automatically merged by LangGraph)
{
    "session_id": "sess_123",           # preserved
    "requirement_text": "Build...",     # preserved
    "extracted_keywords": ["user"...],  # updated
    "status": "requirement_submitted",  # updated
    "current_agent": "search",          # updated
}
```

---

## Hybrid Search

Combines semantic similarity (70%) + keyword matching (30%):

```python
# Example from app/rag/hybrid_search.py
final_score = (0.7 * semantic_score) + (0.3 * keyword_score)

# Tune weights based on query type:
# - Technical queries: 50/50 (exact terms matter)
# - Conceptual queries: 80/20 (meaning matters more)
# - Known keywords: 30/70 (exact match preferred)
```

**Search across 3 collections:**
- `epics` - Historical project epics
- `estimations` - Effort estimation data
- `tdds` - Technical Design Documents

---

## Troubleshooting Quick Links

| Issue | See |
|-------|-----|
| Ollama not connecting | [TROUBLESHOOTING.md#ollama](docs/TROUBLESHOOTING.md#ollama-issues) |
| ChromaDB errors | [TROUBLESHOOTING.md#chromadb](docs/TROUBLESHOOTING.md#chromadb-issues) |
| Agent infinite loops | [TROUBLESHOOTING.md#langgraph](docs/TROUBLESHOOTING.md#langgraph-issues) |
| JSON parsing failures | [TROUBLESHOOTING.md#json](docs/TROUBLESHOOTING.md#json-parsing) |
| Slow search | [TROUBLESHOOTING.md#performance](docs/TROUBLESHOOTING.md#performance) |

---

## Next Steps Based on Your Role

### 👨‍💻 **New Developer**
1. Complete the [Quick Start](#quick-start-5-minutes) above
2. Read [ARCHITECTURE.md](docs/ARCHITECTURE.md) to understand system design
3. Explore component READMEs: [requirement](app/components/requirement/README.md), [historical_match](app/components/historical_match/README.md)
4. Try modifying an existing component using [HOW_TO_GUIDE.md](docs/HOW_TO_GUIDE.md)

### 🏗️ **Architect**
1. Review [ARCHITECTURE.md](docs/ARCHITECTURE.md) for design decisions
2. Understand LangGraph workflow in [orchestrator/workflow.py](app/components/orchestrator/workflow.py)
3. Review RAG layer design in [app/rag/](app/rag/)

### 🐛 **Debugging Issues**
1. Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues
2. Review session audit trails in `sessions/{date}/{session_id}/`
3. Enable debug logging: `export LOG_LEVEL=DEBUG`

### 🧪 **Testing**
1. Run test suite: `pytest -v`
2. Add tests following patterns in `tests/` directory
3. Use `pytest --cov` for coverage reporting

### 🔧 **DevOps/Deployment**
1. Review [TROUBLESHOOTING.md#deployment](docs/TROUBLESHOOTING.md#deployment)
2. Configure environment variables (see `.env.example`)
3. Set `ENVIRONMENT=production` in production

---

## Environment Variables

Create `.env` file (copy from `.env.example`):

```bash
# Application
APP_NAME="AI Impact Assessment System"
ENVIRONMENT=development
LOG_LEVEL=INFO

# Server
HOST=0.0.0.0
PORT=8000

# Ollama (Local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_GEN_MODEL=phi3:mini
OLLAMA_EMBED_MODEL=all-minilm
OLLAMA_TEMPERATURE=0.3

# ChromaDB (Vector Store)
CHROMA_PERSIST_DIR=./data/chroma
CHROMA_COLLECTION_PREFIX=impact_assessment

# Search Tuning
SEARCH_SEMANTIC_WEIGHT=0.70
SEARCH_KEYWORD_WEIGHT=0.30
SEARCH_MAX_RESULTS=10
```

---

## Audit Trail

Every session creates a detailed audit trail:

```
sessions/2024-01-15/sess_20240115_103045_a1b2c3/
├── step1_input/
│   ├── requirement.json
│   └── extracted_keywords.json
├── step2_search/
│   ├── search_request.json
│   ├── all_matches.json
│   └── selected_matches.json
├── step3_agents/
│   ├── agent_impacted_modules/
│   │   ├── input_prompt.txt
│   │   ├── raw_response.txt
│   │   └── parsed_output.json
│   ├── agent_estimation_effort/
│   ├── agent_tdd/
│   └── agent_jira_stories/
└── final_summary.json
```

Use `AuditTrailManager` in services:

```python
from app.utils.audit import AuditTrailManager

audit = AuditTrailManager(session_id="sess_123")
audit.save_json("output.json", data, subfolder="step3_agents/agent_my_component")
audit.save_text("prompt.txt", prompt_text, subfolder="step3_agents/agent_my_component")
```

---

## Performance Tips

| Tip | Impact |
|-----|--------|
| Use `phi3:mini` (not `llama3`) | 3x faster generation |
| Limit `SEARCH_MAX_RESULTS` to 10 | Faster search, less noise |
| Enable ChromaDB persistence | Avoid reindexing on restart |
| Use async endpoints | Handle concurrent requests |
| Monitor session audit trails | Identify slow agents |

---

## Contributing

1. **Follow the component pattern** - Extend `BaseComponent`, create models, service, agent, router
2. **Add tests** - Maintain test coverage above 80%
3. **Document your changes** - Update component README + relevant docs
4. **Use type hints** - Leverage Pydantic for type safety
5. **Handle errors gracefully** - Use component-specific exceptions from `base/exceptions.py`

---

## Support

- **Documentation:** [docs/](docs/) directory
- **API Docs:** http://localhost:8000/docs
- **Component READMEs:** Each `app/components/{name}/README.md`
- **Architecture Deep-Dive:** [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **Development Recipes:** [HOW_TO_GUIDE.md](docs/HOW_TO_GUIDE.md)

---

## License

Internal Elevance Health SDLC project.

---

**Built with:** FastAPI • LangGraph • ChromaDB • Ollama • Pydantic
