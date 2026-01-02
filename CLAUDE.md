# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ele-sdlc-backend

## Repository Ecosystem

| Repository | Type | Purpose | Location |
|------------|------|---------|----------|
| **ele-sdlc-backend** | Private | LangGraph multi-agent API for SDLC knowledge base | `../ele-sdlc-backend/` |
| ele-sdlc-frontend | Private | React/Next.js UI for querying SDLC agents | `../ele-sdlc-frontend/` |

> **This is the backend API repository.** It serves as the source of truth for:
> - API endpoint definitions
> - Data models and entity relationships
> - Agent logic and prompt templates
> - Vector search configuration

## Cross-Repository Context

### Relationship to Frontend

The frontend consumes this API. When modifying endpoints:
1. Check if frontend code depends on the response shape
2. Document breaking changes clearly
3. Consider backwards compatibility or coordinate frontend updates

### API Contract

```
Frontend ──► GET  /health              → { status: "healthy" }
Frontend ──► POST /query (planned)     → { answer: "...", sources: [...] }
```

## Git Operation Safety

**CRITICAL**: You are in `ele-sdlc-backend`. Verify before running git commands:

```bash
pwd  # Should show: .../ele-sdlc-backend
git status  # Should show backend files only
```

**Do NOT** run git commands from the parent directory or frontend repo accidentally.

---

## Project Overview

Enterprise SDLC knowledge base system built with LangGraph multi-agent architecture. Enables AI agents to answer questions about software development projects by traversing relationships between Epics, Estimations, TDDs, Stories/Tasks, and GitLab code references.

## Essential Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the main workflow
python main.py

# Start the API server (default port 8000, configurable via API_PORT env)
python api_server.py

# Run tests
pytest
pytest -v tests/test_specific.py::test_function  # single test
pytest --asyncio-mode=auto  # for async tests

# Scaffold a new project (for reference)
python scaffold_repo.py /path/to/dir --name my_project --dry-run

# Convenience scripts
./start_dev.sh  # Start the API server
./stop_dev.sh   # Stop the API server
```

## Architecture

### Data Flow & Entity Relationships

```
Epic (1) ──┬── Estimation (1:1)
           └── TDD (1:1) ── TDD Sections (1:N) ── Stories/Tasks (1:N) ── GitLab Code (1:1)
```

Agents traverse this hierarchy for contextual answers: Code → Story → TDD Section → Epic → Estimation

### Source Code Structure

- **`src/agents/`** - LangGraph agent implementations (classification, resolution, etc.)
- **`src/graph/`** - LangGraph workflow definitions and state machines
- **`src/models/`** - Pydantic data schemas for state and messages
- **`src/prompts/`** - LLM prompt templates
- **`src/utils/`** - Shared utilities (logging, config loading)
- **`src/vectorstore/`** - FAISS vector store operations for semantic search

### Data Layer

- **`data/raw/`** - Source CSV/JSON files (epics, estimations, tdds, stories_tasks, gitlab_code)
- **`data/processed/`** - Transformed data for ingestion
- **`data/faiss_index/`** - FAISS vector indices
- **`docs/DATA_SCHEMA_README.md`** - Detailed entity schema documentation

### Key Data Files

| File | Purpose | Primary Key |
|------|---------|-------------|
| `epics.csv` | Root entities for projects | `epic_id` |
| `estimations.csv` | Dev/QA effort per epic | `estimation_id` → `epic_id` |
| `tdds.csv` | Technical Design Documents with sections | `tdd_section_id` → `epic_id` |
| `stories_tasks.csv` | Jira-style work items | `story_id` → `tdd_section_id` |
| `gitlab_code.json` | Code traceability | `code_id` → `story_id` |

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
OPENAI_API_KEY=sk-...
CLASSIFICATION_MODEL=gpt-4o-mini    # Fast model for routing
RESOLUTION_MODEL=gpt-4o             # Capable model for answers
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.7
TOP_K_SIMILAR_TICKETS=20            # Vector search limit
API_PORT=8000
```

## API Endpoints

- `GET /health` - Health check

## Vector Search Strategy

Embed these fields for semantic search:
- `epic_title + epic_description` (one chunk per epic)
- `tdd_section_name + tdd_section_content_summary` (one chunk per section)
- `story_title + acceptance_criteria` (one chunk per story)
- `code_block_description + functions_defined` (one chunk per code block)

Include as metadata for filtering: `epic_id`, `status`, `priority`, `team`, `technologies`, `labels`

## Adding New Features Checklist

Before adding utilities or shared logic, ask:
- **Is this needed by frontend too?** → Define clear API contract
- **Is this Python-specific processing?** → Keep it here
- **Does this change data models?** → Update both repos' understanding
