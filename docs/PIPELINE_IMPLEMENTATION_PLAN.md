# Data Engineering Pipeline Implementation Plan

## Executive Summary

This document outlines the implementation plan for adding a Data Engineering Pipeline backend to the ele-sdlc-backend repository. The pipeline transforms source documents (DOCX, XLSX) into structured CSV files that feed the AI Impact Assessment System's ChromaDB vector database.

---

## High-Level Approach

### Architecture Decision

The pipeline will be implemented as a **separate FastAPI application** (`pipeline/main.py`) running on port 8001, distinct from the existing assessment API on port 8000. This approach:

1. **Maintains separation of concerns** - Document processing is distinct from assessment orchestration
2. **Allows independent scaling** - Pipeline can run separately or alongside the main API
3. **Reduces risk** - Changes to pipeline don't affect the production assessment system
4. **Reuses existing code** - Leverages Ollama client, JSON repair utilities, and configuration patterns

### Data Flow

```
Source Documents → Extractors → Raw Data → Transformers → Target Schemas → CSV Export → ChromaDB Sync
     ↓                                          ↓
  DOCX/XLSX           Mapping Review      ID Generation &
                      (User confirms)     FK Relationships
```

---

## Implementation Phases

### Phase 1: Foundation & Schemas (Sections 2-4)

**Goal**: Create the folder structure and Pydantic models that match existing CSV schemas exactly.

### Phase 2: Document Extractors (Section 5)

**Goal**: Parse DOCX and XLSX files into structured raw data with confidence scoring.

### Phase 3: Core Infrastructure (Section 6)

**Goal**: Implement ID generation and relationship tracking for entity linkage.

### Phase 4: Data Transformers (Section 7)

**Goal**: Convert raw extracted data to validated target schemas.

### Phase 5: API Layer (Section 8)

**Goal**: Expose the pipeline through FastAPI endpoints.

### Phase 6: Services & Business Logic (Section 9)

**Goal**: Orchestrate the extraction, transformation, and export workflow.

### Phase 7: Batch Mode (Section 10)

**Goal**: Enable folder-watching for automated processing.

### Phase 8: LLM Prompts & Configuration (Sections 11-12)

**Goal**: Create extraction prompts and configuration files.

### Phase 9: Documentation & Testing (Sections 13-14)

**Goal**: Update CLAUDE.md and create test structure.

---

## Detailed File-by-File Plan

### PHASE 1: Foundation & Schemas

#### 1.1 Create Folder Structure

**Files to create** (all `__init__.py` files):

```
pipeline/
├── __init__.py
├── api/
│   ├── __init__.py
│   └── routes/
│       └── __init__.py
├── core/
│   └── __init__.py
├── extractors/
│   └── __init__.py
├── transformers/
│   └── __init__.py
├── validators/
│   └── __init__.py
├── exporters/
│   └── __init__.py
├── watchers/
│   └── __init__.py
├── prompts/
│   (empty directory, will contain .txt files)
├── models/
│   └── __init__.py
└── services/
    └── __init__.py

shared/
├── __init__.py
└── schemas/
    └── __init__.py

data/pipeline/
├── inbox/
├── processing/
├── completed/
├── failed/
└── jobs/
```

**Rationale**: Following the existing `app/components/` structure pattern but adapted for a document processing pipeline.

---

#### 1.2 Shared Pydantic Schemas

These models must **exactly match** the existing CSV column schemas.

##### File: `shared/schemas/epic.py`

**Purpose**: Epic entity schema matching `data/raw/epics.csv`

**Columns from CSV**:
- `epic_id` (PK, format: EPIC-NNN)
- `epic_name`
- `req_id`
- `jira_id` (e.g., MM16783)
- `req_description` (multi-paragraph text)
- `status` (Literal: "Planning", "In Progress", "Done", "Blocked")
- `epic_priority` (Literal: "Critical", "High", "Medium", "Low")
- `epic_owner` (email format)
- `epic_team` (e.g., "Commerce", "Platform", "Healthcare")
- `epic_start_date` (date, ISO format)
- `epic_target_date` (date, ISO format)
- `created_at` (datetime with timezone)
- `updated_at` (datetime with timezone)

**Implementation Notes**:
- Use `@field_validator` for email validation on `epic_owner`
- Use `Literal` types for status and priority enums
- Use `Optional[date]` for date fields with None as default
- Add `@classmethod` `csv_columns()` returning ordered column list
- Add `@classmethod` `from_extracted_data(data: dict)` factory method

**Location**: `/Users/arunnaudiyal/Elevance Health/SDLC/Code/ele-sdlc-backend/shared/schemas/epic.py`

---

##### File: `shared/schemas/estimation.py`

**Purpose**: Estimation entity schema matching `data/raw/estimations.csv`

**Columns from CSV**:
- `dev_est_id` (PK, format: EST-NNN)
- `epic_id` (FK to epics)
- `module_id` (format: MOD-{DOMAIN}-NNN)
- `task_description`
- `complexity` (Literal: "Small", "Medium", "Large")
- `dev_effort_hours` (float)
- `qa_effort_hours` (float)
- `total_effort_hours` (float, calculated)
- `total_story_points` (int)
- `risk_level` (Literal: "Low", "Medium", "High")
- `estimation_method` (e.g., "Planning Poker", "T-Shirt Sizing")
- `confidence_level` (Literal: "Low", "Medium", "High")
- `estimated_by` (email)
- `estimation_date` (date)
- `other_params` (JSON object as string)

**Implementation Notes**:
- Add `@field_validator` to auto-calculate `total_effort_hours = dev_effort_hours + qa_effort_hours`
- Add `@field_serializer` to convert `other_params` dict to JSON string
- Validate `epic_id` starts with "EPIC-"

**Location**: `/Users/arunnaudiyal/Elevance Health/SDLC/Code/ele-sdlc-backend/shared/schemas/estimation.py`

---

##### File: `shared/schemas/tdd.py`

**Purpose**: TDD entity schema matching `data/raw/tdds.csv`

**Columns from CSV**:
- `tdd_id` (PK, format: TDD-NNN)
- `epic_id` (FK to epics)
- `dev_est_id` (FK to estimations)
- `tdd_name`
- `tdd_description` (multi-paragraph)
- `tdd_version` (e.g., "1.0", "1.2")
- `tdd_status` (Literal: "Draft", "In Review", "Approved")
- `tdd_author` (email)
- `technical_components` (JSON array as string)
- `design_decisions`
- `tdd_dependencies` (JSON array as string)
- `architecture_pattern`
- `security_considerations`
- `performance_requirements`
- `created_at` (datetime)
- `updated_at` (datetime)

**Implementation Notes**:
- Add `@field_serializer` for `technical_components` and `tdd_dependencies` to convert lists to JSON strings
- Default `tdd_version` to "1.0"
- Validate FK prefixes

**Location**: `/Users/arunnaudiyal/Elevance Health/SDLC/Code/ele-sdlc-backend/shared/schemas/tdd.py`

---

##### File: `shared/schemas/story.py`

**Purpose**: Story entity schema matching `data/raw/stories_tasks.csv`

**Columns from CSV**:
- `jira_story_id` (PK, e.g., "MMO-12323" or "STORY-NNN")
- `dev_est_id` (FK to estimations)
- `epic_id` (FK to epics)
- `tdd_id` (FK to tdds)
- `issue_type` (Literal: "Story", "Task", "Sub-task", "Bug")
- `summary`
- `description`
- `assignee` (email)
- `status` (Literal: "To Do", "In Progress", "Done", "Blocked")
- `story_points` (float)
- `sprint` (e.g., "Sprint-25")
- `priority` (Literal: "Critical", "High", "Medium", "Low")
- `labels` (JSON array as string)
- `acceptance_criteria`
- `story_created_date` (date)
- `story_updated_date` (date)
- `other_params` (JSON object as string)

**Implementation Notes**:
- Validate Jira ID format with regex: `[A-Z]+-\d+`
- Add `@field_serializer` for `labels` and `other_params`
- All three FK fields should validate prefixes

**Location**: `/Users/arunnaudiyal/Elevance Health/SDLC/Code/ele-sdlc-backend/shared/schemas/story.py`

---

### PHASE 2: Document Extractors

#### 2.1 Base Extractor

##### File: `pipeline/extractors/base.py`

**Purpose**: Abstract base class and data models for all extractors

**Classes**:
1. `ExtractedData` (Pydantic model):
   - `raw_content: str` - Full document text
   - `structured_fields: Dict[str, Any]` - Key-value pairs found
   - `tables: List[Dict[str, Any]]` - Extracted tables
   - `lists: List[Dict[str, Any]]` - Extracted lists
   - `confidence_scores: Dict[str, float]` - Per-field confidence
   - `metadata: Dict[str, Any]` - Document properties

2. `BaseExtractor` (ABC):
   - `@abstractmethod async extract(file_path: Path) -> ExtractedData`
   - `@abstractmethod get_supported_extensions() -> List[str]`
   - `get_confidence_score() -> float` - Overall extraction confidence

**Location**: `/Users/arunnaudiyal/Elevance Health/SDLC/Code/ele-sdlc-backend/pipeline/extractors/base.py`

---

#### 2.2 DOCX Extractor

##### File: `pipeline/extractors/docx_extractor.py`

**Purpose**: Parse Word documents into structured data

**Dependencies**: `python-docx>=0.8.11` (add to requirements.txt)

**Implementation**:
1. Use `python-docx` to open document
2. Extract document properties (title, author, created, modified)
3. Process paragraphs with style detection:
   - Heading 1, 2, 3 → hierarchy tracking
   - Normal → content paragraphs
4. Extract tables:
   - First row as headers
   - Remaining rows as data dicts
5. Detect patterns via regex:
   - Jira IDs: `[A-Z]+-\d+` or `MM\d+`
   - Emails: `[\w.-]+@[\w.-]+\.\w+`
   - Dates: Multiple formats
   - Key: Value pairs

**Location**: `/Users/arunnaudiyal/Elevance Health/SDLC/Code/ele-sdlc-backend/pipeline/extractors/docx_extractor.py`

---

#### 2.3 Excel Extractor

##### File: `pipeline/extractors/excel_extractor.py`

**Purpose**: Parse Excel spreadsheets into structured data

**Dependencies**: `openpyxl>=3.1.2` (add to requirements.txt)

**Implementation**:
1. Use `openpyxl` to load workbook
2. Iterate through sheets
3. Auto-detect header row (first row with string values)
4. Handle merged cells by propagating values
5. Convert Excel date serial numbers to Python dates
6. Extract formula results (not formulas themselves)
7. Return dict keyed by sheet name

**Location**: `/Users/arunnaudiyal/Elevance Health/SDLC/Code/ele-sdlc-backend/pipeline/extractors/excel_extractor.py`

---

#### 2.4 LLM Extractor

##### File: `pipeline/extractors/llm_extractor.py`

**Purpose**: Enhance extraction using Ollama LLM for field identification

**Reuses**:
- `app/utils/ollama_client.py` - `get_ollama_client()`
- `app/utils/json_repair.py` - `parse_llm_json()`

**Implementation**:
1. Load prompts from `pipeline/prompts/`
2. `async enhance_extraction(extracted: ExtractedData, target_entity: str) -> EnhancedExtraction`
   - Format prompt with extracted text
   - Call Ollama for field identification
   - Parse response with `parse_llm_json()`
   - Return enhanced data with confidence scores
3. `async suggest_field_mappings(extracted: ExtractedData, target_schema: Type[BaseModel]) -> List[FieldMapping]`
   - Analyze extracted fields
   - Suggest mappings to target schema fields
   - Return with confidence per mapping

**Location**: `/Users/arunnaudiyal/Elevance Health/SDLC/Code/ele-sdlc-backend/pipeline/extractors/llm_extractor.py`

---

### PHASE 3: Core Infrastructure

#### 3.1 ID Generator

##### File: `pipeline/core/id_generator.py`

**Purpose**: Generate unique primary keys with format enforcement

**Implementation**:
```python
class IDGenerator:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.counters = {"epic": 0, "estimation": 0, "tdd": 0, "story": 0, "module": 0}
        self.used_ids: Set[str] = set()

    def generate_epic_id(self, prefix: str = "EPIC") -> str:
        self.counters["epic"] += 1
        id = f"{prefix}-{self.counters['epic']:03d}"
        self.used_ids.add(id)
        return id

    def generate_estimation_id(self, prefix: str = "EST") -> str:
        # Similar pattern

    def generate_tdd_id(self, prefix: str = "TDD") -> str:
        # Similar pattern

    def generate_story_id(self, jira_id: Optional[str] = None) -> str:
        if jira_id and self.is_valid_jira_id(jira_id):
            return jira_id
        self.counters["story"] += 1
        return f"STORY-{self.counters['story']:03d}"

    def generate_module_id(self, domain: str) -> str:
        domain_upper = domain.upper()[:3]
        self.counters["module"] += 1
        return f"MOD-{domain_upper}-{self.counters['module']:03d}"

    @staticmethod
    def is_valid_jira_id(jira_id: str) -> bool:
        return bool(re.match(r'^[A-Z]+-\d+$', jira_id)) or bool(re.match(r'^MM\d+$', jira_id))
```

**Location**: `/Users/arunnaudiyal/Elevance Health/SDLC/Code/ele-sdlc-backend/pipeline/core/id_generator.py`

---

#### 3.2 Relationship Manager

##### File: `pipeline/core/relationship_manager.py`

**Purpose**: Track entity relationships and validate FK integrity

**Implementation**:
```python
class RelationshipManager:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.epic_map: Dict[str, str] = {}          # source_id -> epic_id
        self.estimation_map: Dict[str, str] = {}     # epic_id -> dev_est_id
        self.tdd_map: Dict[str, str] = {}            # epic_id -> tdd_id
        self.story_map: Dict[str, List[str]] = {}    # (epic_id, tdd_id) -> [story_ids]

    def register_epic(self, source_identifier: str, epic_id: str) -> None:
        self.epic_map[source_identifier] = epic_id

    def link_estimation_to_epic(self, epic_id: str, dev_est_id: str) -> None:
        self.estimation_map[epic_id] = dev_est_id

    # ... other methods as specified

    def validate_all_relationships(self) -> List[ValidationError]:
        errors = []
        # Check all estimations have valid epic_id
        # Check all TDDs have valid epic_id and dev_est_id
        # Check all stories have valid epic_id, dev_est_id, tdd_id
        return errors
```

**Location**: `/Users/arunnaudiyal/Elevance Health/SDLC/Code/ele-sdlc-backend/pipeline/core/relationship_manager.py`

---

### PHASE 4: Data Transformers

#### 4.1 Base Transformer

##### File: `pipeline/transformers/base.py`

**Purpose**: Abstract base class for all transformers

**Implementation**:
```python
class BaseTransformer(ABC, Generic[TTarget]):
    @abstractmethod
    async def transform(
        self,
        extracted: ExtractedData,
        mapping: Dict[str, str],
        id_gen: IDGenerator,
        rel_mgr: RelationshipManager
    ) -> TTarget:
        pass

    @abstractmethod
    def validate(self, data: TTarget) -> List[ValidationError]:
        pass

    @abstractmethod
    def get_target_schema(self) -> Type[BaseModel]:
        pass
```

**Location**: `/Users/arunnaudiyal/Elevance Health/SDLC/Code/ele-sdlc-backend/pipeline/transformers/base.py`

---

#### 4.2 Normalizers

##### File: `pipeline/transformers/normalizers.py`

**Purpose**: Utility functions for data normalization

**Functions**:
1. `date_normalizer(value: Any) -> Optional[date]`
   - Handle: ISO, US, European formats, Excel serial dates
2. `datetime_normalizer(value: Any) -> Optional[datetime]`
   - Add UTC timezone if missing
3. `array_to_json_string(value: Any) -> str`
   - Convert list to JSON, pass through existing strings
4. `enum_normalizer(value: str, allowed: List[str], default: Optional[str]) -> str`
   - Case-insensitive matching, fuzzy match if needed
5. `email_normalizer(value: str) -> str`
   - Validate and lowercase
6. `clean_text(value: str) -> str`
   - Strip whitespace, normalize unicode

**Location**: `/Users/arunnaudiyal/Elevance Health/SDLC/Code/ele-sdlc-backend/pipeline/transformers/normalizers.py`

---

#### 4.3 Entity Transformers

##### Files:
- `pipeline/transformers/epic_transformer.py`
- `pipeline/transformers/estimation_transformer.py`
- `pipeline/transformers/tdd_transformer.py`
- `pipeline/transformers/story_transformer.py`

Each transformer:
1. Extends `BaseTransformer[TargetSchema]`
2. Applies field mappings from extracted data
3. Generates IDs using `IDGenerator`
4. Registers relationships using `RelationshipManager`
5. Applies normalizers for dates, enums, emails
6. Returns validated schema instance

**Transformation Order** (critical for FK relationships):
1. Epics first (no dependencies)
2. Estimations second (need epic_id)
3. TDDs third (need epic_id, dev_est_id)
4. Stories last (need all three FKs)

---

### PHASE 5: API Layer

#### 5.1 Main Application

##### File: `pipeline/main.py`

**Purpose**: FastAPI application for pipeline

**Implementation**:
- Create FastAPI app on port 8001
- Add CORS middleware (same origins as main app)
- Include route modules
- Startup event: Initialize JobTracker, verify Ollama
- Exception handlers for common errors

**Pattern**: Follow `app/main.py` structure

**Location**: `/Users/arunnaudiyal/Elevance Health/SDLC/Code/ele-sdlc-backend/pipeline/main.py`

---

#### 5.2 Route Modules

##### File: `pipeline/api/routes/health.py`
- `GET /api/v1/pipeline/health` - Status, version, Ollama status, disk space

##### File: `pipeline/api/routes/upload.py`
- `POST /api/v1/pipeline/upload` - Multipart form with files
- `GET /api/v1/pipeline/jobs/{job_id}/files` - List uploaded files

##### File: `pipeline/api/routes/extract.py`
- `POST /api/v1/pipeline/extract/{job_id}` - Run extraction
- `GET /api/v1/pipeline/mapping-suggestions/{job_id}` - Get AI suggestions
- `POST /api/v1/pipeline/apply-mapping/{job_id}` - Apply mappings

##### File: `pipeline/api/routes/transform.py`
- `POST /api/v1/pipeline/transform/{job_id}` - Transform to target schemas

##### File: `pipeline/api/routes/preview.py`
- `GET /api/v1/pipeline/preview/{job_id}` - Preview data
- `GET /api/v1/pipeline/validation/{job_id}` - Validate data

##### File: `pipeline/api/routes/export.py`
- `POST /api/v1/pipeline/export/{job_id}` - Export CSVs
- `GET /api/v1/pipeline/export/{job_id}/download/{filename}` - Download file

##### File: `pipeline/api/routes/batch.py`
- `POST /api/v1/pipeline/batch/start` - Start watcher
- `POST /api/v1/pipeline/batch/stop` - Stop watcher
- `GET /api/v1/pipeline/batch/status` - Watcher status
- `GET /api/v1/pipeline/batch/jobs` - List batch jobs
- `GET /api/v1/pipeline/batch/jobs/{job_id}` - Job details

---

### PHASE 6: Services

#### 6.1 Job Tracker

##### File: `pipeline/services/job_tracker.py`

**Purpose**: Track pipeline job state and artifacts

**Reuses pattern from**: `app/utils/audit.py` (AuditTrailManager)

**Job State Structure**:
```json
{
    "job_id": "JOB-20250128-001",
    "job_type": "interactive",
    "status": "extracting",
    "current_step": "extract",
    "steps_completed": ["upload"],
    "files_uploaded": [...],
    "created_at": "...",
    "updated_at": "...",
    "error_message": null,
    "metadata": {}
}
```

**Location**: `/Users/arunnaudiyal/Elevance Health/SDLC/Code/ele-sdlc-backend/pipeline/services/job_tracker.py`

---

#### 6.2 Service Modules

##### Files:
- `pipeline/services/upload_service.py` - File upload handling
- `pipeline/services/extraction_service.py` - Orchestrate extractors
- `pipeline/services/transformation_service.py` - Orchestrate transformers
- `pipeline/services/export_service.py` - CSV export and vector sync
- `pipeline/services/batch_service.py` - Batch job management

---

### PHASE 7: Batch Mode

#### 7.1 Folder Watcher

##### File: `pipeline/watchers/folder_watcher.py`

**Purpose**: Monitor inbox folder for new document sets

**Dependencies**: `watchdog>=3.0.0` (add to requirements.txt)

**Implementation**:
- Use `watchdog.observers.Observer`
- Monitor `data/pipeline/inbox/`
- On folder creation, validate contents and queue for processing

---

#### 7.2 Batch Processor

##### File: `pipeline/watchers/batch_processor.py`

**Purpose**: Auto-process folders through pipeline

**Implementation**:
- Move folder to `processing/`
- Run full pipeline with auto-mapping
- Move to `completed/` or `failed/`

---

### PHASE 8: LLM Prompts & Configuration

#### 8.1 LLM Prompts

**Files** (as specified in Section 11):
- `pipeline/prompts/epic_extraction.txt`
- `pipeline/prompts/estimation_extraction.txt`
- `pipeline/prompts/tdd_extraction.txt`
- `pipeline/prompts/story_extraction.txt`

---

#### 8.2 Configuration

##### File: `config/pipeline_settings.yaml`
- Pipeline, extractor, transformer, batch, export settings

##### File: `pipeline/core/config.py`
- `PipelineSettings` Pydantic model
- `get_pipeline_settings()` with `@lru_cache`

---

### PHASE 9: Documentation & Testing

#### 9.1 Update CLAUDE.md

Add Data Engineering Pipeline section as specified in Section 13.

#### 9.2 Test Structure

Create `tests/pipeline/` directory with test files as specified in Section 14.

---

## Dependencies to Add

Add to `requirements.txt`:
```
# Pipeline dependencies
python-docx>=0.8.11
openpyxl>=3.1.2
watchdog>=3.0.0
python-multipart>=0.0.6
aiofiles>=23.2.1
```

---

## Challenges & Mitigations

### 1. Document Format Variability
**Challenge**: Source documents may have inconsistent formatting.
**Mitigation**: LLM extractor provides fallback for low-confidence extractions.

### 2. Relationship Linking
**Challenge**: Matching entities across documents without explicit IDs.
**Mitigation**: RelationshipManager uses multiple identifiers (Jira ID, name, position).

### 3. Large File Processing
**Challenge**: Large Excel files may cause memory issues.
**Mitigation**: Use streaming/chunked processing where possible.

### 4. LLM Response Quality
**Challenge**: Ollama may return malformed JSON.
**Mitigation**: Reuse existing `parse_llm_json()` with repair strategies.

---

## Execution Order

1. **Create folder structure** (all `__init__.py` files and data directories)
2. **Implement shared schemas** (epic, estimation, tdd, story)
3. **Implement extractors** (base, docx, excel, llm)
4. **Implement core** (id_generator, relationship_manager, config)
5. **Implement transformers** (base, normalizers, entity transformers)
6. **Implement validators** (schema, relationship, quality)
7. **Implement exporters** (csv, json, vector_sync)
8. **Implement services** (job_tracker, upload, extraction, transformation, export, batch)
9. **Implement API routes** (health, upload, extract, transform, preview, export, batch)
10. **Implement main.py** (FastAPI app)
11. **Implement watchers** (folder_watcher, batch_processor)
12. **Create LLM prompts** (all .txt files)
13. **Create configuration** (yaml and config.py)
14. **Update CLAUDE.md**
15. **Create test structure**
16. **Update requirements.txt**

---

## Verification Steps

After each phase:
1. Verify Python syntax: `python -m py_compile <file>`
2. Run type checking: `mypy pipeline/`
3. Test imports: `python -c "from pipeline import ..."`
4. After Phase 5: Start server and test health endpoint
5. After Phase 6: Test full extraction workflow
6. After Phase 7: Test batch folder processing
