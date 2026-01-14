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
python scripts/reindex.py  # Delete existing before rebuild
```

## Architecture

### LangGraph Workflow Pipeline

```
requirement → historical_match → auto_select → impacted_modules
           → estimation_effort → tdd → jira_stories → code_impact → risks → END
```

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

### RAG Layer (`app/rag/`)

- `embeddings.py` - Ollama embedding service
- `vector_store.py` - ChromaDB wrapper (singleton pattern)
- `hybrid_search.py` - Fuses semantic (70%) and keyword (30%) scores

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
- `data/raw/` - Source CSV files for indexing
- `data/uploads/` - Uploaded requirement files
- `sessions/` - Session audit trails (JSON logs per session)

## Adding a New Component

1. Create `app/components/{name}/` directory
2. Add `models.py` with Pydantic request/response types
3. Create service extending `BaseComponent[TRequest, TResponse]`
4. Add agent wrapper function for LangGraph
5. Create router with FastAPI endpoints
6. Register router in `app/main.py`
7. Add node and edges in `orchestrator/workflow.py` if part of pipeline

## Cross-Repository Context

Frontend at `../ele-sdlc-frontend/` consumes this API. When modifying endpoints, check frontend dependencies. API contract changes require coordination.
