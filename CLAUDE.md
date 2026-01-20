# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Impact Assessment System: A FastAPI backend with LangGraph multi-agent orchestration for analyzing software requirements. Takes requirement descriptions, finds historical matches via hybrid search (semantic + keyword), and generates impact assessments including TDDs, effort estimates, Jira stories, code impact, and risks.

**Tech stack**: FastAPI, LangGraph, ChromaDB (vector store), Ollama (local LLM), Pydantic

## Essential Commands

```bash
# Start development (handles Ollama, models, ChromaDB, and server)
./start_dev.sh

# Or manually:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Stop all services
./stop_dev.sh

# Initialize/rebuild vector database
python scripts/init_vector_db.py
python scripts/reindex.py && python scripts/init_vector_db.py  # Full reindex

# Testing
pytest                                       # Run all tests
pytest -v                                    # Verbose output
pytest tests/test_file.py                    # Single file
pytest tests/test_file.py::test_function     # Single test
pytest --asyncio-mode=auto                   # Async tests

# Verify Ollama is running
curl http://localhost:11434/api/tags

# Health check
curl http://localhost:8000/api/v1/health
```

## Architecture

### LangGraph Workflow Pipeline

```
requirement → historical_match → auto_select → impacted_modules
           → estimation_effort → tdd → jira_stories → END
```

(Note: `code_impact` and `risks` agents exist but are currently disabled in the workflow)

Workflow defined in `app/components/orchestrator/workflow.py`. Each agent is a node that receives state and returns partial state updates.

### Component Structure Pattern

Each feature lives in `app/components/{feature}/` with standard files:
- `models.py` - Pydantic request/response schemas
- `service.py` - Business logic implementing `BaseComponent[TRequest, TResponse]`
- `agent.py` - LangGraph node wrapper (calls service, returns state dict)
- `router.py` - FastAPI endpoints
- `prompts.py` - LLM prompt templates (if applicable)

Components:
- `session` - Session management
- `file_input` - File upload handling
- `requirement` - Requirement parsing and keyword extraction
- `historical_match` - Hybrid search for similar past work
- `impacted_modules` - Module impact analysis
- `estimation_effort` - Effort estimation
- `tdd` - Technical Design Document generation
- `jira_stories` - Jira story generation
- `code_impact` - Code impact analysis
- `risks` - Risk assessment
- `orchestrator` - LangGraph workflow coordination

### State Flow

Agents return partial state updates (only changed fields). State is defined in `app/components/orchestrator/state.py`. Key fields:
- `session_id`, `requirement_text` - Input
- `extracted_keywords`, `all_matches`, `selected_matches` - Intermediate
- `status`, `current_agent`, `error_message` - Control flow
- `messages` - Accumulated via `operator.add` reducer (append-only)

Status progression: `created → requirement_submitted → matches_found → matches_selected → impacted_modules_generated → estimation_effort_completed → tdd_generated → jira_stories_generated → code_impact_generated → risks_generated → completed`

### RAG Layer (`app/rag/`)

- `embeddings.py` - Ollama embedding service
- `vector_store.py` - ChromaDB wrapper (singleton via `get_instance()`)
- `hybrid_search.py` - Fuses semantic (70%) and keyword (30%) scores

Singleton pattern: Services use `@classmethod get_instance()` for thread-safe singletons. Settings use `@lru_cache` in `get_settings()`.

### LLM Response Parsing

Agents use `app/utils/json_repair.py` to handle malformed LLM JSON responses. Always use `parse_llm_json()` instead of raw `json.loads()` when parsing Ollama outputs - it handles common issues like trailing commas, unquoted keys, and truncated responses.

### Configuration

Settings loaded via Pydantic from environment or `config/settings.yaml`:
- `app/components/base/config.py` - Settings class with all config options
- Override via `.env` file (uses `OLLAMA_*`, `CHROMA_*`, `SEARCH_*` prefixes)

Default models: `phi3:mini` (generation), `all-minilm` (embeddings)

## API Endpoints

All under `/api/v1/`:
- `GET /health` - Health check (includes Ollama status)
- `GET /config` - Current configuration
- `POST /sessions` - Create session
- `POST /sessions/{id}/requirements` - Submit requirement
- `POST /sessions/{id}/historical-matches` - Search historical data
- `POST /sessions/{id}/select-matches` - Select matches for analysis
- `POST /orchestrator/run` - Execute full pipeline
- `POST /orchestrator/run-from-file` - Pipeline from uploaded file

## Data Storage

- `data/chroma/` - ChromaDB vector indices (epics, estimations, tdds collections)
- `data/raw/` - Source CSV files for indexing (epics.csv, estimations.csv, tdds.csv, stories_tasks.csv, gitlab_code.json)
- `data/uploads/` - Uploaded requirement files
- `sessions/` - Session audit trails per session, organized by date/session_id

Session output structure:
```
sessions/{date}/{session_id}/
├── step1_input/           # requirement.json, extracted_keywords.json
├── step2_search/          # search_request.json, all_matches.json, selected_matches.json
├── step3_agents/
│   ├── agent_tdd/         # input_prompt.txt, raw_response.txt, tdd.md, parsed_output.json
│   └── ...
└── final_summary.json
```

Use `AuditTrailManager(session_id)` in services to save artifacts (see `app/utils/audit.py`).

## Adding a New Component

1. Create `app/components/{name}/` directory
2. Add `models.py` with Pydantic request/response types
3. Create service extending `BaseComponent[TRequest, TResponse]`
4. Add agent wrapper function for LangGraph (see `tdd/agent.py` for pattern)
5. Create router with FastAPI endpoints
6. Register router in `app/main.py`
7. Add node and edges in `orchestrator/workflow.py` if part of pipeline

Agent wrapper pattern (from `tdd/agent.py`):
```python
async def my_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node - returns partial state updates."""
    service = get_service()
    request = MyRequest(session_id=state["session_id"], ...)
    response = await service.process(request)
    return {
        "my_output": response.model_dump(),
        "status": "my_step_done",
        "current_agent": "next_agent",
        "messages": [{"role": "my_agent", "content": "..."}],
    }
```

## Cross-Repository Context

Frontend at `../ele-sdlc-frontend/` consumes this API. When modifying endpoints, check frontend dependencies. API contract changes require coordination.

---

## Data Engineering Pipeline

A separate FastAPI service (port 8001) for processing source documents into structured CSV files that feed the main assessment system's vector database.

### Pipeline Overview

```
Source Documents (DOCX, XLSX)
         ↓
    [EXTRACT] → Structured fields from documents
         ↓
    [MAP] → Field mapping to target schema
         ↓
    [TRANSFORM] → Normalized data with IDs/FKs
         ↓
    [VALIDATE] → Schema + relationship checks
         ↓
    [EXPORT] → CSV files → data/raw/
```

### Pipeline Commands

```bash
# Start pipeline API (port 8001)
uvicorn pipeline.main:app --host 0.0.0.0 --port 8001 --reload

# Or use the module directly
python -m pipeline.main

# Run batch processor (watches inbox folder)
python -m pipeline.watchers.batch_processor
```

### Pipeline Structure

```
pipeline/
├── api/routes/          # FastAPI endpoints
│   ├── health.py        # GET /health
│   ├── upload.py        # POST /upload, GET /jobs/{id}/files
│   ├── extract.py       # POST /extract/{id}, GET /mapping-suggestions/{id}
│   ├── transform.py     # POST /transform/{id}
│   ├── preview.py       # GET /preview/{id}, GET /validation/{id}
│   ├── export.py        # POST /export/{id}, GET /export/{id}/{entity}
│   └── batch.py         # Batch processing endpoints
├── core/
│   ├── config.py        # PipelineSettings (pydantic-settings)
│   ├── id_generator.py  # ID generation (EPIC-001, EST-001, etc.)
│   └── relationship_manager.py  # FK tracking, position-based linking
├── extractors/
│   ├── base.py          # BaseExtractor, ExtractedData dataclass
│   ├── docx_extractor.py   # python-docx extraction
│   ├── excel_extractor.py  # openpyxl extraction
│   └── llm_extractor.py    # Ollama enhancement for low-confidence extractions
├── transformers/
│   ├── base.py          # BaseTransformer, TransformationResult
│   ├── normalizers.py   # date_normalizer, array_to_json_string, etc.
│   ├── epic_transformer.py
│   ├── estimation_transformer.py
│   ├── tdd_transformer.py
│   └── story_transformer.py
├── models/
│   ├── api_models.py    # Request/Response Pydantic models
│   ├── pipeline_job.py  # PipelineJob, JobStatus, JobStep enums
│   └── source_documents.py  # SourceDocument, DocumentType
├── services/
│   └── job_tracker.py   # Job state management
├── watchers/
│   ├── folder_watcher.py   # watchdog-based file monitoring
│   └── batch_processor.py  # Automated pipeline execution
├── prompts/             # LLM prompt templates
└── main.py              # FastAPI application
```

### Pipeline Data Directories

```
data/pipeline/
├── inbox/       # Drop files here for batch processing
├── processing/  # Files being processed
├── completed/   # Successful job outputs
├── failed/      # Failed job files
├── jobs/        # Job state and artifacts
│   └── {job_id}/
│       ├── state.json
│       ├── uploads/
│       ├── extracted/
│       ├── transformed/
│       └── exported/
└── output/      # Final CSV outputs
```

### Two Modes of Operation

**Interactive Mode** (API-driven):
1. `POST /upload` - Upload files, get job_id
2. `POST /extract/{job_id}` - Extract structured data
3. `GET /mapping-suggestions/{job_id}` - Get AI-suggested field mappings
4. `POST /apply-mapping/{job_id}` - Confirm mappings
5. `POST /transform/{job_id}` - Transform to target schema
6. `GET /validation/{job_id}` - Validate relationships
7. `POST /export/{job_id}` - Export CSVs

**Batch Mode** (folder watcher):
- Drop files in `data/pipeline/inbox/`
- Files are auto-grouped by project prefix
- Full pipeline runs automatically
- Output appears in `data/pipeline/completed/`

### Target CSV Schemas

Schemas in `shared/schemas/` match existing `data/raw/*.csv` files:
- `Epic` - 13 columns (epic_id, epic_name, req_id, jira_id, ...)
- `Estimation` - 15 columns (estimation_id, module_name, epic_id, ...)
- `TDD` - 16 columns (tdd_id, tdd_name, epic_id, dev_est_id, ...)
- `Story` - 17 columns (story_id, story_title, epic_id, jira_id, ...)

### ID Generation Pattern

- `EPIC-001`, `EPIC-002`, ... (per job)
- `EST-001`, `EST-002`, ...
- `TDD-001`, `TDD-002`, ...
- `STORY-001`, `STORY-002`, ...
- `MOD-{entity_prefix}-001` for modules

### Relationship Linking

Position-based FK linking:
- First epic links to first estimation
- Estimations link to corresponding TDDs by order
- Stories link to epics by position

### Configuration

Settings in `config/pipeline_settings.yaml`:
- Pipeline port (8001)
- Directory paths
- Ollama settings
- Extraction/transformation defaults
- Batch processing options

Override with environment variables:
- `PIPELINE_PORT`, `PIPELINE_DEBUG`
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
- `EXTRACTION_LLM_CONFIDENCE_THRESHOLD`
