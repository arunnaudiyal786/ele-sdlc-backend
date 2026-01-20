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

### Testing Ollama Server

Use these commands to verify Ollama is functioning correctly:

#### List Available Models

```bash
curl http://localhost:11434/api/tags | jq '.models[].name'
```

#### Send a Test Query

```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "phi3:mini",
    "prompt": "Say hello in one word",
    "stream": false
  }'
```

#### Test JSON Format Output (Used by Backend)

```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "phi3:mini",
    "prompt": "Return a JSON object with name and age fields for a person named John who is 30",
    "format": "json",
    "stream": false
  }'
```

#### Test Embedding Model

```bash
curl -X POST http://localhost:11434/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "all-minilm",
    "prompt": "Test embedding generation"
  }'
```

> **Note**: Use `stream: false` for simpler testing (returns complete response). Use `format: "json"` to force JSON output, which is how the backend agents work.

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
| Pipeline API | http://localhost:8001 | Data Engineering Pipeline |
| Frontend | http://localhost:3000 | React/Next.js UI |
| Ollama | http://localhost:11434 | Local LLM runtime |
| ChromaDB | ./data/chroma | Vector store (file-based) |

---

# Data Engineering Pipeline

The Data Engineering Pipeline is a **separate FastAPI service** (port 8001) that transforms source documents (DOCX, XLSX) into structured CSV files. These CSVs feed the main assessment system's vector database.

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Data Engineering Pipeline                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Source Documents                     Target CSV Files              │
│   ┌──────────────┐                    ┌──────────────┐              │
│   │ Epic.docx    │                    │ epics.csv    │              │
│   │ Estimate.xlsx│  ──► PIPELINE ──►  │ estimations  │              │
│   │ TDD.docx     │                    │ tdds.csv     │              │
│   │ Stories.docx │                    │ stories.csv  │              │
│   └──────────────┘                    └──────────────┘              │
│                                              │                       │
│                                              ▼                       │
│                                       ┌──────────────┐              │
│                                       │   ChromaDB   │              │
│                                       │ Vector Store │              │
│                                       └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

### Pipeline Stages

| Stage | Description | Output |
|-------|-------------|--------|
| **UPLOAD** | Receive source documents (DOCX, XLSX) | Files stored in job directory |
| **EXTRACT** | Parse documents, extract structured fields | JSON extraction artifacts |
| **MAP** | AI-suggested field mappings to target schema | Confirmed field mappings |
| **TRANSFORM** | Normalize data, generate IDs, link FKs | Transformed entity data |
| **VALIDATE** | Schema compliance, FK integrity checks | Validation report |
| **EXPORT** | Generate final CSV files | CSV files ready for ChromaDB |

---

## Pipeline Quick Start

```bash
# 1. Ensure virtual environment is active
cd ele-sdlc-backend
source ../.venv/bin/activate

# 2. Start Ollama (if not already running)
ollama serve &

# 3. Start the Pipeline API (port 8001)
uvicorn pipeline.main:app --host 0.0.0.0 --port 8001 --reload

# 4. Verify it's running
curl http://localhost:8001/api/v1/pipeline/health
```

---

## Two Modes of Operation

The pipeline supports **two distinct modes**:

| Mode | Use Case | How It Works |
|------|----------|--------------|
| **Interactive** | Manual control, field mapping review | API-driven, step-by-step |
| **Batch** | Automated processing | Drop files in inbox, auto-process |

---

## Interactive Mode (API-Driven)

Interactive mode gives you full control over each pipeline stage with the ability to review and modify field mappings.

### Step 1: Upload Documents

Upload your source documents to create a new pipeline job.

```bash
# Upload files (at minimum, estimation XLSX is required)
curl -X POST http://localhost:8001/api/v1/pipeline/upload \
  -F "epic_doc=@/path/to/epic_requirements.docx" \
  -F "estimation_doc=@/path/to/estimation_sheet.xlsx" \
  -F "tdd_doc=@/path/to/technical_design.docx" \
  -F "stories_doc=@/path/to/user_stories.docx"
```

**Response:**

```json
{
  "job_id": "JOB-20260119-001",
  "status": "uploaded",
  "files_received": [
    {"filename": "epic_requirements.docx", "size": 45678, "type": ".docx", "document_type": "epic"},
    {"filename": "estimation_sheet.xlsx", "size": 123456, "type": ".xlsx", "document_type": "estimation"},
    {"filename": "technical_design.docx", "size": 78901, "type": ".docx", "document_type": "tdd"},
    {"filename": "user_stories.docx", "size": 34567, "type": ".docx", "document_type": "story"}
  ],
  "message": "Successfully uploaded 4 file(s)"
}
```

> **Note**: Save the `job_id` - you'll need it for all subsequent steps.

### Step 2: Extract Data

Run extraction to parse documents and extract structured fields.

```bash
# Extract with LLM enhancement for low-confidence extractions
curl -X POST http://localhost:8001/api/v1/pipeline/extract/JOB-20260119-001 \
  -H "Content-Type: application/json" \
  -d '{"use_llm_enhancement": true, "llm_confidence_threshold": 0.7}'
```

**Response:**

```json
{
  "job_id": "JOB-20260119-001",
  "status": "extracted",
  "extractions": {
    "epic_requirements.docx": {
      "document_type": "epic",
      "fields_count": 12,
      "tables_count": 0,
      "jira_ids": ["PROJ-123", "PROJ-124"],
      "emails": ["owner@company.com"],
      "confidence": 0.87,
      "warnings": []
    },
    "estimation_sheet.xlsx": {
      "document_type": "estimation",
      "fields_count": 45,
      "tables_count": 1,
      "jira_ids": [],
      "emails": [],
      "confidence": 0.92,
      "warnings": []
    }
  },
  "overall_confidence": 0.89,
  "message": "Extracted data from 4 file(s)"
}
```

### Step 3: Get Mapping Suggestions (Optional)

Get AI-suggested field mappings for any entity type.

```bash
# Get mapping suggestions for estimations
curl http://localhost:8001/api/v1/pipeline/mapping-suggestions/JOB-20260119-001?entity=estimation
```

**Response:**

```json
{
  "job_id": "JOB-20260119-001",
  "entity_type": "estimation",
  "suggestions": [
    {
      "source_field": "Module",
      "target_field": "module_name",
      "confidence": 0.95,
      "source_value": "Authentication Service",
      "reasoning": "Direct semantic match for module identifier"
    },
    {
      "source_field": "Dev Hours",
      "target_field": "estimated_dev_hours",
      "confidence": 0.92,
      "source_value": "16",
      "reasoning": "Numeric hours value for development effort"
    }
  ],
  "unmapped_fields": ["risks", "assumptions"]
}
```

### Step 4: Apply Field Mappings

Confirm or customize the field mappings for each entity.

```bash
# Apply mappings for estimation entity
curl -X POST "http://localhost:8001/api/v1/pipeline/apply-mapping/JOB-20260119-001?entity=estimation" \
  -H "Content-Type: application/json" \
  -d '{
    "Module": "module_name",
    "Dev Hours": "estimated_dev_hours",
    "QA Hours": "estimated_qa_hours",
    "Description": "task_description",
    "Complexity": "complexity"
  }'
```

**Response:**

```json
{
  "job_id": "JOB-20260119-001",
  "status": "mapping_applied",
  "entity": "estimation",
  "applied_mappings": {
    "Module": "module_name",
    "Dev Hours": "estimated_dev_hours",
    "QA Hours": "estimated_qa_hours",
    "Description": "task_description",
    "Complexity": "complexity"
  }
}
```

### Step 5: Transform Data

Transform extracted data to the target schema with proper IDs and relationships.

```bash
curl -X POST http://localhost:8001/api/v1/pipeline/transform/JOB-20260119-001
```

**Response:**

```json
{
  "job_id": "JOB-20260119-001",
  "status": "transformed",
  "records_created": {
    "epics": 1,
    "estimations": 15,
    "tdds": 1,
    "stories": 8
  },
  "relationship_summary": {
    "epic_count": 1,
    "estimation_count": 15,
    "tdd_count": 1,
    "story_count": 8,
    "estimation_to_epic_links": 15,
    "tdd_to_epic_links": 1,
    "story_to_epic_links": 8
  },
  "validation_warnings": [],
  "message": "Transformed 25 total records"
}
```

### Step 6: Preview Transformed Data

Preview the transformed data before final export.

```bash
# Preview estimations (paginated)
curl "http://localhost:8001/api/v1/pipeline/preview/JOB-20260119-001?entity=estimations&limit=5&offset=0"
```

**Response:**

```json
{
  "job_id": "JOB-20260119-001",
  "entity": "estimations",
  "data": [
    {
      "estimation_id": "EST-001",
      "module_name": "Authentication Service",
      "epic_id": "EPIC-001",
      "task_description": "Implement OAuth 2.0 flow",
      "estimated_dev_hours": 16.0,
      "estimated_qa_hours": 8.0,
      "complexity": "Medium",
      "total_effort_hours": 24.0
    }
  ],
  "total_count": 15,
  "validation_results": {}
}
```

### Step 7: Validate Data

Run full validation to check schema compliance and FK integrity.

```bash
curl http://localhost:8001/api/v1/pipeline/validation/JOB-20260119-001
```

**Response:**

```json
{
  "job_id": "JOB-20260119-001",
  "valid": true,
  "errors": [],
  "warnings": [],
  "relationship_integrity": {
    "total_entities": 25,
    "total_relationships": 24,
    "broken_links": 0
  }
}
```

### Step 8: Export to CSV

Export validated data to CSV files.

```bash
curl -X POST http://localhost:8001/api/v1/pipeline/export/JOB-20260119-001
```

**Response:**

```json
{
  "job_id": "JOB-20260119-001",
  "status": "completed",
  "files_exported": [
    {"entity": "epics", "file_path": "data/pipeline/completed/JOB-20260119-001/epics.csv", "record_count": 1},
    {"entity": "estimations", "file_path": "data/pipeline/completed/JOB-20260119-001/estimations.csv", "record_count": 15},
    {"entity": "tdds", "file_path": "data/pipeline/completed/JOB-20260119-001/tdds.csv", "record_count": 1},
    {"entity": "stories", "file_path": "data/pipeline/completed/JOB-20260119-001/stories.csv", "record_count": 8}
  ],
  "total_records": 25,
  "export_path": "data/pipeline/completed/JOB-20260119-001",
  "message": "Exported 25 records to 4 files"
}
```

### Step 9: Download Individual CSV Files

Download a specific entity's CSV file.

```bash
# Download estimations CSV
curl http://localhost:8001/api/v1/pipeline/export/JOB-20260119-001/estimations \
  -o estimations.csv
```

### Step 10: Sync to Vector Database (Optional)

Sync exported data to the main vector database.

```bash
curl -X POST http://localhost:8001/api/v1/pipeline/sync-vector-db/JOB-20260119-001
```

**Response:**

```json
{
  "job_id": "JOB-20260119-001",
  "status": "synced",
  "synced_files": [
    {"entity": "epics", "new_records": 1, "target_path": "data/raw/epics.csv"},
    {"entity": "estimations", "new_records": 15, "target_path": "data/raw/estimations.csv"}
  ],
  "message": "Data synced to raw data directory. Run reindex script to update vector DB.",
  "next_step": "python scripts/reindex.py && python scripts/init_vector_db.py"
}
```

After syncing, reindex ChromaDB:

```bash
python scripts/reindex.py && python scripts/init_vector_db.py
```

---

## Interactive Mode - Complete Workflow Script

Here's a complete bash script for the interactive workflow:

```bash
#!/bin/bash
# interactive_pipeline.sh - Complete interactive pipeline workflow

# Configuration
PIPELINE_URL="http://localhost:8001/api/v1/pipeline"
EPIC_DOC="./docs/epic_requirements.docx"
ESTIMATION_DOC="./docs/estimation_sheet.xlsx"
TDD_DOC="./docs/technical_design.docx"
STORIES_DOC="./docs/user_stories.docx"

echo "=== Data Engineering Pipeline - Interactive Mode ==="

# Step 1: Upload
echo -e "\n[1/8] Uploading documents..."
UPLOAD_RESPONSE=$(curl -s -X POST "$PIPELINE_URL/upload" \
  -F "epic_doc=@$EPIC_DOC" \
  -F "estimation_doc=@$ESTIMATION_DOC" \
  -F "tdd_doc=@$TDD_DOC" \
  -F "stories_doc=@$STORIES_DOC")

JOB_ID=$(echo $UPLOAD_RESPONSE | jq -r '.job_id')
echo "Job created: $JOB_ID"

# Step 2: Extract
echo -e "\n[2/8] Extracting data..."
curl -s -X POST "$PIPELINE_URL/extract/$JOB_ID" \
  -H "Content-Type: application/json" \
  -d '{"use_llm_enhancement": true}' | jq '.overall_confidence'

# Step 3: Get mapping suggestions
echo -e "\n[3/8] Getting mapping suggestions..."
curl -s "$PIPELINE_URL/mapping-suggestions/$JOB_ID?entity=estimation" | jq '.suggestions[:3]'

# Step 4: Apply default mappings (auto)
echo -e "\n[4/8] Applying mappings..."
for entity in epic estimation tdd story; do
  curl -s -X POST "$PIPELINE_URL/apply-mapping/$JOB_ID?entity=$entity" \
    -H "Content-Type: application/json" \
    -d '{}' > /dev/null
done
echo "Mappings applied for all entities"

# Step 5: Transform
echo -e "\n[5/8] Transforming data..."
curl -s -X POST "$PIPELINE_URL/transform/$JOB_ID" | jq '.records_created'

# Step 6: Preview
echo -e "\n[6/8] Previewing transformed data..."
curl -s "$PIPELINE_URL/preview/$JOB_ID?entity=estimations&limit=3" | jq '.data'

# Step 7: Validate
echo -e "\n[7/8] Validating data..."
VALIDATION=$(curl -s "$PIPELINE_URL/validation/$JOB_ID")
echo $VALIDATION | jq '{valid: .valid, errors: .errors | length, warnings: .warnings | length}'

# Step 8: Export
echo -e "\n[8/8] Exporting to CSV..."
curl -s -X POST "$PIPELINE_URL/export/$JOB_ID" | jq '.files_exported'

echo -e "\n=== Pipeline Complete ==="
echo "Output directory: data/pipeline/completed/$JOB_ID/"
```

---

## Batch Mode (Automated Processing)

Batch mode automatically processes files dropped into the inbox directory.

### Starting Batch Mode

**Option 1: Run batch processor directly**

```bash
python -m pipeline.watchers.batch_processor
```

**Option 2: Use the batch API endpoints**

```bash
# Check what's in the inbox
curl http://localhost:8001/api/v1/pipeline/batch/queue

# Trigger processing of all queued files
curl -X POST http://localhost:8001/api/v1/pipeline/batch/process
```

### Batch Mode File Naming Convention

Files are grouped by **project prefix**. Name your files consistently:

```
data/pipeline/inbox/
├── projectA_epic.docx        # Epic for Project A
├── projectA_estimation.xlsx  # Estimation for Project A
├── projectA_tdd.docx         # TDD for Project A
├── projectA_stories.docx     # Stories for Project A
├── projectB_epic.docx        # Epic for Project B
├── projectB_estimation.xlsx  # Estimation for Project B
└── ...
```

**Recognized patterns:**
- `*_epic.docx` or `epic_*.docx` → Epic document
- `*_estimation.xlsx` or `estimation_*.xlsx` → Estimation document
- `*_tdd.docx` or `tdd_*.docx` → TDD document
- `*_stories.docx` or `*_story.docx` → Stories document

### Batch Processing Workflow

```bash
# 1. Create inbox directory (if not exists)
mkdir -p data/pipeline/inbox

# 2. Copy files to inbox
cp project_epic.docx data/pipeline/inbox/
cp project_estimation.xlsx data/pipeline/inbox/
cp project_tdd.docx data/pipeline/inbox/

# 3. Start batch processor (runs continuously)
python -m pipeline.watchers.batch_processor

# Output will show:
# 2026-01-19 10:30:15 - INFO - Batch mode running. Watching for files...
# 2026-01-19 10:30:16 - INFO - New file detected: project_epic.docx
# 2026-01-19 10:30:16 - INFO - New file detected: project_estimation.xlsx
# 2026-01-19 10:30:18 - INFO - File grouped: project_epic.docx -> project/epic
# 2026-01-19 10:30:20 - INFO - Processing file group for project: project
# 2026-01-19 10:30:25 - INFO - Pipeline completed successfully for job JOB-20260119-002
```

### Check Batch Job Status

```bash
# Get status of all batch jobs
curl http://localhost:8001/api/v1/pipeline/batch/status
```

**Response:**

```json
{
  "summary": {
    "pending": 0,
    "processing": 1,
    "completed": 5,
    "failed": 1
  },
  "jobs": {
    "pending": [],
    "processing": [
      {"job_id": "JOB-20260119-003", "status": "transforming", "created_at": "2026-01-19T10:35:00Z", "files_count": 3}
    ],
    "completed": [
      {"job_id": "JOB-20260119-001", "status": "completed", "created_at": "2026-01-19T09:00:00Z", "files_count": 4}
    ],
    "failed": [
      {"job_id": "JOB-20260118-005", "status": "failed", "created_at": "2026-01-18T15:30:00Z", "files_count": 2}
    ]
  }
}
```

### Retry Failed Jobs

```bash
# Retry a specific failed job
curl -X POST http://localhost:8001/api/v1/pipeline/batch/retry/JOB-20260118-005
```

### Delete Old Jobs

```bash
# Delete a completed or failed job
curl -X DELETE http://localhost:8001/api/v1/pipeline/batch/job/JOB-20260118-005
```

---

## Pipeline Directory Structure

After running the pipeline, files are organized as follows:

```
data/pipeline/
├── inbox/                      # Drop files here for batch processing
│   └── (files waiting to be processed)
│
├── processing/                 # Files currently being processed
│   └── JOB-YYYYMMDD-NNN/
│       └── (uploaded files)
│
├── jobs/                       # Job state and artifacts
│   └── JOB-YYYYMMDD-NNN/
│       ├── state.json          # Job state (status, steps, results)
│       ├── uploads/            # Original uploaded files
│       ├── extracted/          # Extraction artifacts
│       │   ├── epic.docx_extraction.json
│       │   ├── estimation.xlsx_extraction.json
│       │   └── epic_mapping.json
│       ├── transformed/        # Transformed data
│       │   ├── epics_transformed.json
│       │   ├── estimations_transformed.json
│       │   └── relationship_graph.json
│       └── exported/           # Export metadata
│           └── export_metadata.json
│
├── completed/                  # Successfully processed outputs
│   └── JOB-YYYYMMDD-NNN/
│       ├── epics.csv
│       ├── estimations.csv
│       ├── tdds.csv
│       └── stories.csv
│
├── failed/                     # Failed job files (for debugging)
│   └── JOB-YYYYMMDD-NNN/
│       └── (original files + error info)
│
└── output/                     # Final consolidated output
```

---

## Pipeline API Reference

### Upload Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/pipeline/upload` | POST | Upload documents, create job |
| `/api/v1/pipeline/jobs/{job_id}/files` | GET | List files for a job |

### Extraction Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/pipeline/extract/{job_id}` | POST | Extract data from documents |
| `/api/v1/pipeline/mapping-suggestions/{job_id}` | GET | Get AI field mapping suggestions |
| `/api/v1/pipeline/apply-mapping/{job_id}` | POST | Apply confirmed mappings |

### Transformation Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/pipeline/transform/{job_id}` | POST | Transform to target schema |

### Preview & Validation Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/pipeline/preview/{job_id}` | GET | Preview transformed data |
| `/api/v1/pipeline/validation/{job_id}` | GET | Run validation checks |

### Export Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/pipeline/export/{job_id}` | POST | Export to CSV files |
| `/api/v1/pipeline/export/{job_id}/{entity}` | GET | Download specific CSV |
| `/api/v1/pipeline/sync-vector-db/{job_id}` | POST | Sync to main data/raw/ |

### Batch Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/pipeline/batch/queue` | GET | List files in inbox |
| `/api/v1/pipeline/batch/process` | POST | Trigger batch processing |
| `/api/v1/pipeline/batch/status` | GET | Get all batch job statuses |
| `/api/v1/pipeline/batch/retry/{job_id}` | POST | Retry failed job |
| `/api/v1/pipeline/batch/job/{job_id}` | DELETE | Delete job and files |

### Health Endpoint

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/pipeline/health` | GET | Pipeline health check |

---

## Pipeline Configuration

### Configuration File

Edit `config/pipeline_settings.yaml`:

```yaml
# Pipeline Service Settings
pipeline:
  port: 8001
  debug: false

# Directory Paths
paths:
  base: "data/pipeline"
  jobs: "data/pipeline/jobs"
  inbox: "data/pipeline/inbox"
  processing: "data/pipeline/processing"
  completed: "data/pipeline/completed"
  failed: "data/pipeline/failed"
  output: "data/pipeline/output"

# File Upload Limits
upload:
  docx_max_size_mb: 10
  excel_max_size_mb: 50

# Ollama LLM Settings
ollama:
  base_url: "http://localhost:11434"
  model: "phi3:mini"
  embedding_model: "all-minilm"
  timeout: 60
  temperature: 0.1

# Extraction Settings
extraction:
  llm_confidence_threshold: 0.7
  use_llm_enhancement: true
  max_table_rows: 1000

# Batch Processing Settings
batch:
  enabled: true
  file_stability_seconds: 2.0
  max_concurrent_jobs: 3
```

### Environment Variable Overrides

Override settings via environment variables:

```bash
# Pipeline settings
export PIPELINE_PORT=8001
export PIPELINE_DEBUG=true

# Ollama settings
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=phi3:mini

# Extraction settings
export EXTRACTION_LLM_CONFIDENCE_THRESHOLD=0.7
export EXTRACTION_USE_LLM_ENHANCEMENT=true

# Batch settings
export BATCH_ENABLED=true
export BATCH_MAX_CONCURRENT_JOBS=5
```

---

## Target CSV Schemas

The pipeline produces CSVs matching these schemas (same as `data/raw/*.csv`):

### epics.csv (13 columns)

| Column | Type | Description |
|--------|------|-------------|
| epic_id | string | Primary key (EPIC-001) |
| epic_name | string | Epic title |
| req_id | string | Requirement ID |
| jira_id | string | Jira epic ID |
| req_description | text | Full description |
| status | string | Active/Completed/On Hold |
| epic_priority | string | High/Medium/Low/Critical |
| epic_owner | string | Owner name |
| epic_team | string | Team name |
| epic_start_date | date | Start date (YYYY-MM-DD) |
| epic_target_date | date | Target date |
| created_at | datetime | Creation timestamp |
| updated_at | datetime | Last update timestamp |

### estimations.csv (15 columns)

| Column | Type | Description |
|--------|------|-------------|
| estimation_id | string | Primary key (EST-001) |
| module_name | string | Module/component name |
| epic_id | string | FK to epics |
| dev_est_id | string | Development estimation ID |
| task_description | text | Task description |
| estimated_dev_hours | float | Dev hours |
| estimated_qa_hours | float | QA hours |
| estimated_ba_hours | float | BA hours |
| estimated_pm_hours | float | PM hours |
| total_effort_hours | float | Auto-calculated total |
| complexity | string | Simple/Medium/Complex/High |
| assumptions | text | Assumptions |
| dependencies | text | Dependencies |
| risks | text | Known risks |
| created_at | datetime | Creation timestamp |

### tdds.csv (16 columns)

| Column | Type | Description |
|--------|------|-------------|
| tdd_id | string | Primary key (TDD-001) |
| tdd_name | string | TDD title |
| epic_id | string | FK to epics |
| dev_est_id | string | FK to estimations |
| tdd_description | text | Technical design summary |
| tdd_author | string | Author name |
| tdd_reviewer | string | Reviewer name |
| tdd_status | string | Draft/In Review/Approved |
| technical_components | JSON | Component list as JSON array |
| tdd_dependencies | JSON | Dependencies as JSON array |
| architecture_changes | text | Architecture changes |
| database_changes | text | DB changes |
| api_changes | text | API changes |
| security_considerations | text | Security notes |
| performance_considerations | text | Performance notes |
| created_at | datetime | Creation timestamp |

### stories.csv (17 columns)

| Column | Type | Description |
|--------|------|-------------|
| story_id | string | Primary key (STORY-001) |
| story_title | string | Story title |
| epic_id | string | FK to epics |
| jira_id | string | Jira story ID |
| story_description | text | User story text |
| story_type | string | Story/Bug/Task/Spike |
| story_status | string | To Do/In Progress/Done |
| story_points | int | Story points |
| story_priority | string | Highest/High/Medium/Low |
| assignee | string | Assigned person |
| sprint | string | Sprint name |
| labels | JSON | Labels as JSON array |
| acceptance_criteria | text | AC text |
| technical_notes | text | Tech notes |
| linked_tdd_id | string | FK to TDDs |
| linked_estimation_id | string | FK to estimations |
| created_at | datetime | Creation timestamp |

---

## Pipeline Troubleshooting

### Pipeline Server Won't Start

**Problem**: `ModuleNotFoundError: No module named 'pipeline'`

**Solution**: Ensure you're in the correct directory and packages are installed:

```bash
cd ele-sdlc-backend
pip install -r requirements.txt
pip install -e .  # If setup.py exists
```

### Extraction Fails with Low Confidence

**Problem**: Extraction confidence below threshold, LLM enhancement failing.

**Solution**: Ensure Ollama is running with required models:

```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Pull required model if missing
ollama pull phi3:mini
```

### Foreign Key Validation Errors

**Problem**: `References non-existent epic: EPIC-XXX`

**Solution**: This means a transformed entity references an epic that wasn't extracted. Check:
1. Did you upload the epic document?
2. Are the documents from the same project?
3. Use position-based linking (default) for documents without explicit IDs.

### Batch Files Not Being Processed

**Problem**: Files in inbox aren't being picked up.

**Solution**:
1. Check file naming convention (must include `_epic`, `_estimation`, etc.)
2. Ensure batch processor is running: `python -m pipeline.watchers.batch_processor`
3. At minimum, an estimation file is required to trigger processing.

### CSV Export Has Wrong Columns

**Problem**: Exported CSV doesn't match expected schema.

**Solution**: Check your field mappings. Preview data before export:

```bash
curl "http://localhost:8001/api/v1/pipeline/preview/JOB-XXX?entity=estimations"
```

### Port 8001 Already In Use

**Problem**: `Address already in use`

**Solution**:

```bash
# Find what's using port 8001
lsof -i :8001

# Kill the process or use a different port
uvicorn pipeline.main:app --port 8002 --reload
```

---

## Running Both Services (Full Stack)

### Terminal 1: Main Assessment API (port 8000)

```bash
cd ele-sdlc-backend
source ../.venv/bin/activate
./start_dev.sh  # Starts Ollama, ChromaDB init, and API on 8000
```

### Terminal 2: Data Engineering Pipeline (port 8001)

```bash
cd ele-sdlc-backend
source ../.venv/bin/activate
uvicorn pipeline.main:app --host 0.0.0.0 --port 8001 --reload
```

### Terminal 3: Batch Processor (optional)

```bash
cd ele-sdlc-backend
source ../.venv/bin/activate
python -m pipeline.watchers.batch_processor
```

### Terminal 4: Frontend (port 3000)

```bash
cd ele-sdlc-frontend
npm run dev
```

### All Services Summary

| Service | URL | Purpose |
|---------|-----|---------|
| Assessment API | http://localhost:8000 | Main LangGraph orchestration |
| Pipeline API | http://localhost:8001 | Document processing pipeline |
| Batch Processor | (background) | Auto-process inbox files |
| Frontend | http://localhost:3000 | React/Next.js UI |
| Ollama | http://localhost:11434 | Local LLM runtime |

### Health Check All Services

```bash
# Assessment API
curl http://localhost:8000/api/v1/health

# Pipeline API
curl http://localhost:8001/api/v1/pipeline/health

# Ollama
curl http://localhost:11434/api/tags
```
