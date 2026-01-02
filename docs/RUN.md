# Running the SDLC Backend Application

This guide covers all commands needed to set up and run the AI Impact Assessment Backend from scratch.

## Prerequisites

- **Python 3.10+** (tested with 3.12)
- **Ollama** - Local LLM runtime for embeddings and generation
- **Git** (optional, for version control)

---

## Quick Start (TL;DR)

```bash
# 1. Setup environment (one-time)
cd ele-sdlc-backend
python -m venv ../.venv
source ../.venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit as needed

# 2. Start everything (handles Ollama, models, vector DB, and API)
./start_dev.sh
```

The `start_dev.sh` script automatically:
- Starts Ollama server if not running
- Pulls required models (`all-minilm`, `phi3:mini`) if missing
- Initializes ChromaDB vector store if empty
- Starts the FastAPI server

---

## Detailed Setup

### 1. Create Virtual Environment

```bash
# From project root
cd ele-sdlc-backend

# Create virtual environment (one level up to share across repos)
python -m venv ../.venv

# Activate it
source ../.venv/bin/activate  # macOS/Linux
# OR
..\.venv\Scripts\activate     # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` with your settings:

```ini
# Application
APP_ENV=development
DEBUG=true

# Ollama (Local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_GEN_MODEL=phi3:mini
OLLAMA_EMBED_MODEL=all-minilm
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_TEMPERATURE=0.3

# ChromaDB (Vector Store)
CHROMA_PERSIST_DIR=./data/chroma

# Search Configuration
SEARCH_SEMANTIC_WEIGHT=0.70
SEARCH_KEYWORD_WEIGHT=0.30
SEARCH_MAX_RESULTS=10

# Data Paths
DATA_RAW_PATH=./data/raw
DATA_UPLOADS_PATH=./data/uploads
DATA_SESSIONS_PATH=./data/sessions

# Server
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

> **Important**: `CORS_ORIGINS` must be a JSON array format, not comma-separated.

---

## Starting Ollama

Ollama provides local LLM capabilities for embeddings and text generation.

### Install Ollama (if not installed)

```bash
# macOS
brew install ollama

# Or download from https://ollama.ai
```

### Start Ollama Server

```bash
# Start in background
ollama serve &

# OR start in a separate terminal
ollama serve
```

### Pull Required Models

```bash
# Embedding model (required for vector search)
ollama pull all-minilm

# Generation model (required for LLM responses)
ollama pull phi3:mini
```

### Verify Ollama is Running

```bash
curl http://localhost:11434/api/tags
```

---

## Initialize Vector Database

Before running the application, you must populate the ChromaDB vector store with your SDLC data.

### Prepare Data Files

Ensure your data files exist in `data/raw/`:

```
data/raw/
├── epics.csv
├── estimations.csv
├── tdds.csv
├── stories_tasks.csv
└── gitlab_code.json
```

### Run Initialization Script

```bash
python scripts/init_vector_db.py
```

Expected output:

```
Initializing ChromaDB at ./data/chroma
Loading data from data/raw
Indexed 3 epics
Indexed 3 estimations
Indexed 3 TDD sections
Indexed 3 stories
Indexed 9 code blocks
Initialization complete!
Collections: ['impact_assessment_stories', 'impact_assessment_epics', ...]
```

---

## Starting the API Server

### Option 1: Full automated setup (Recommended)

```bash
./start_dev.sh
```

This script handles everything:
1. Checks if Ollama is installed
2. Starts Ollama server if not running
3. Waits for Ollama to be ready
4. Pulls `all-minilm` and `phi3:mini` models if missing
5. Initializes ChromaDB if empty
6. Starts the FastAPI server with hot-reload

### Option 2: Using uvicorn directly (manual setup)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Using Python directly

```bash
python api_server.py
```

The API will be available at: `http://localhost:8000`

### Verify Server is Running

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "ollama": "connected"
}
```

---

## Stopping the Server

```bash
./stop_dev.sh
```

Or press `Ctrl+C` if running in foreground.

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check with Ollama status |
| `/api/v1/config` | GET | Current configuration |
| `/api/v1/sessions` | POST | Create analysis session |
| `/api/v1/requirements` | GET/POST | Manage requirements |
| `/api/v1/search` | POST | Semantic search |
| `/api/v1/modules` | GET | Get modules |
| `/api/v1/effort` | GET | Effort estimations |
| `/api/v1/stories` | GET | Stories and tasks |
| `/api/v1/code-impact` | GET | Code impact analysis |
| `/api/v1/risks` | GET | Risk assessment |
| `/api/v1/orchestrator` | POST | Full orchestration |

### Interactive API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Reindexing Data

If you need to rebuild the vector database:

### Delete All Collections

```bash
python scripts/reindex.py
```

### Repopulate Data

```bash
python scripts/init_vector_db.py
```

### One-liner

```bash
python scripts/reindex.py && python scripts/init_vector_db.py
```

---

## Running with Input Files (File-Based Pipeline)

This section describes how to run the impact assessment pipeline using a JSON input file instead of making direct API calls.

### Prerequisites

Before running file-based pipeline execution:

1. **Ollama running** with required models (`all-minilm`, `phi3:mini`)
2. **ChromaDB initialized** with `python scripts/init_vector_db.py`
3. **API server running** via `./start_dev.sh` or `python api_server.py`

### Step 1: Create Input File

Create a JSON file in the `input/` directory with your requirement:

```bash
# Create input file
cat > input/new_req.txt << 'EOF'
{
  "session_id": "my-epic-001",
  "requirement_text": "Your requirement or epic description goes here. Be detailed about the functionality, constraints, and expected outcomes.",
  "jira_epic_id": "PROJ-123",
  "selected_matches": []
}
EOF
```

**Input File Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | Yes | Unique identifier for tracking (alphanumeric, `-`, `_`) |
| `requirement_text` | string | Yes | The requirement description (min 10 chars) |
| `jira_epic_id` | string | No | Optional Jira epic ID for traceability |
| `selected_matches` | array | No | Pre-selected matches (empty = auto-select top 5) |

**Example - API Modernization Epic:**

```json
{
  "session_id": "api-modernization-001",
  "requirement_text": "Refactor the legacy SOAP-based Customer API to a RESTful microservices architecture. The new API should support JSON payloads, implement OAuth 2.0 authentication, use pagination for large datasets, and include comprehensive OpenAPI documentation.",
  "jira_epic_id": "SDLC-5001",
  "selected_matches": []
}
```

### Step 2: Process the File via API

Call the `/api/v1/impact/process-file` endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/impact/process-file \
  -H "Content-Type: application/json" \
  -d '{"file_path": "input/new_req.txt"}'
```

**Expected Response:**

```json
{
  "session_id": "api-modernization-001",
  "status": "completed",
  "output_path": "data/sessions/2024-01-15/api-modernization-001/",
  "message": "Pipeline completed with status: completed"
}
```

### Step 3: View Output

The pipeline saves results to the session directory:

```bash
# List session outputs
ls data/sessions/$(date +%Y-%m-%d)/my-epic-001/

# View final summary
cat data/sessions/$(date +%Y-%m-%d)/my-epic-001/final_summary.json | jq '.'
```

**Output Directory Structure:**

```
data/sessions/2024-01-15/my-epic-001/
├── step1_input/
│   ├── requirement.json        # Original requirement
│   └── extracted_keywords.json # Keywords extracted
├── step2_search/
│   ├── search_request.json     # Search parameters
│   ├── all_matches.json        # All search results
│   └── selected_matches.json   # Selected matches
└── final_summary.json          # Complete pipeline output
```

### Complete End-to-End Workflow

```bash
# 1. Start the backend (handles Ollama, ChromaDB, and API)
cd ele-sdlc-backend
source ../.venv/bin/activate
./start_dev.sh

# 2. Wait for server to be ready
curl http://localhost:8000/api/v1/health

# 3. Create input file (or use the provided sample)
cat input/new_req.txt

# 4. Process the file
curl -X POST http://localhost:8000/api/v1/impact/process-file \
  -H "Content-Type: application/json" \
  -d '{"file_path": "input/new_req.txt"}'

# 5. Check output
cat data/sessions/$(date +%Y-%m-%d)/api-modernization-001/final_summary.json | jq '.modules, .effort, .risks'
```

### Error Handling

| Error Code | Description | Solution |
|------------|-------------|----------|
| 400 | Invalid file path or JSON schema | Check file path starts with `input/` and JSON is valid |
| 404 | File not found | Verify file exists: `ls input/` |
| 503 | ChromaDB not initialized | Run `python scripts/init_vector_db.py` |

**Example Error Response:**

```json
{
  "error": "ChromaDB not initialized. Run 'python scripts/init_vector_db.py' first.",
  "component": "file_input",
  "details": {
    "missing_collections": ["epics", "estimations"],
    "hint": "python scripts/init_vector_db.py"
  }
}
```

### Auto-Selection Behavior

When `selected_matches` is empty (`[]`), the pipeline automatically:
1. Runs semantic + keyword search across all collections
2. Ranks matches by combined score
3. Selects top 5 matches automatically
4. Continues pipeline execution

To use specific matches, provide them in the input file:

```json
{
  "session_id": "my-epic-002",
  "requirement_text": "...",
  "selected_matches": [
    {"id": "epic-001", "collection": "epics", "score": 0.92},
    {"id": "tdd-003", "collection": "tdds", "score": 0.85}
  ]
}
```

---

## Development Commands

### Run Tests

```bash
pytest
pytest -v                        # Verbose
pytest tests/test_specific.py    # Single file
pytest --asyncio-mode=auto       # Async tests
```

### Check Application Logs

Logs are structured JSON format (via structlog):

```bash
# API server logs appear in terminal
./start_dev.sh 2>&1 | jq '.'
```

---

## Troubleshooting

### Error: `cors_origins` JSON parsing error

**Problem**: `.env` has `CORS_ORIGINS=http://localhost:3000,http://localhost:5173`

**Solution**: Use JSON array format:
```ini
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

### Error: `OllamaUnavailableError`

**Problem**: Ollama server is not running.

**Solution**:
```bash
ollama serve &
# Verify
curl http://localhost:11434/api/tags
```

### Error: `IndexError: list index out of range` during indexing

**Problem**: Empty embeddings returned - usually a data column mismatch.

**Solution**: Verify your CSV column names match what the script expects. Check `scripts/init_vector_db.py` for expected column names.

### Error: Model not found

**Problem**: Required Ollama model not pulled.

**Solution**:
```bash
ollama pull all-minilm   # For embeddings
ollama pull phi3:mini    # For generation
```

### ChromaDB Corruption

**Problem**: ChromaDB in inconsistent state.

**Solution**: Delete and reinitialize:
```bash
rm -rf data/chroma/*
python scripts/init_vector_db.py
```

---

## Full Stack (Frontend + Backend)

### Terminal 1: Backend

```bash
cd ele-sdlc-backend
source ../.venv/bin/activate
./start_dev.sh
```

### Terminal 2: Frontend

```bash
cd ../ele-sdlc-frontend
npm install
npm run dev
```

Access the full application at: `http://localhost:3000`

---

## Environment Summary

| Service | Default URL | Purpose |
|---------|-------------|---------|
| Backend API | http://localhost:8000 | FastAPI server |
| Frontend | http://localhost:3000 | React/Next.js UI |
| Ollama | http://localhost:11434 | Local LLM runtime |
| ChromaDB | ./data/chroma | Vector store (file-based) |
