# AI Impact Assessment System
## Management Presentation

---

# SLIDE 1: Data Engineering Pipeline

## Overview
Transform source enterprise documents into a structured knowledge base for AI-powered impact assessment.

## Source Documents (Input)

```
+------------------+     +------------------+     +------------------+     +------------------+
|   DOCX Files     |     |   Excel Files    |     |   DOCX Files     |     |   DOCX Files     |
|                  |     |                  |     |                  |     |                  |
|  Epic/Requirement|     |   Estimations    |     |      TDDs        |     |  Jira Stories    |
|  Descriptions    |     | (Dev/QA Effort)  |     | (Tech Designs)   |     |    & Tasks       |
+------------------+     +------------------+     +------------------+     +------------------+
```

## Data Engineering Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                           DATA ENGINEERING PIPELINE                                          │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐    │
│  │                              STAGE 1: EXTRACTION                                     │    │
│  │                                                                                      │    │
│  │   DOCX (Epics)        Excel (Est.)        DOCX (TDDs)        DOCX (Stories)         │    │
│  │        │                   │                   │                   │                │    │
│  │        ▼                   ▼                   ▼                   ▼                │    │
│  │   ┌─────────┐         ┌─────────┐         ┌─────────┐         ┌─────────┐          │    │
│  │   │ python- │         │ pandas  │         │ python- │         │ python- │          │    │
│  │   │  docx   │         │ openpyxl│         │  docx   │         │  docx   │          │    │
│  │   └────┬────┘         └────┬────┘         └────┬────┘         └────┬────┘          │    │
│  │        │                   │                   │                   │                │    │
│  └────────┼───────────────────┼───────────────────┼───────────────────┼────────────────┘    │
│           │                   │                   │                   │                     │
│  ┌────────▼───────────────────▼───────────────────▼───────────────────▼────────────────┐    │
│  │                              STAGE 2: TRANSFORMATION                                │    │
│  │                                                                                      │    │
│  │   • Parse structured content (tables, headings, lists)                              │    │
│  │   • Extract key fields (IDs, names, descriptions, dates)                            │    │
│  │   • Normalize data formats (dates, enums, arrays)                                   │    │
│  │   • Validate relationships (epic_id → estimation → story → code)                    │    │
│  │   • Handle missing values and data quality issues                                   │    │
│  │                                                                                      │    │
│  └──────────────────────────────────────────────┬───────────────────────────────────────┘    │
│                                                 │                                            │
│  ┌──────────────────────────────────────────────▼───────────────────────────────────────┐    │
│  │                              STAGE 3: LOAD (RAW FILES)                               │    │
│  │                                                                                      │    │
│  │   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐        │    │
│  │   │  epics.csv    │  │estimations.csv│  │   tdds.csv    │  │stories_tasks  │        │    │
│  │   │               │  │               │  │               │  │    .csv       │        │    │
│  │   │ • epic_id     │  │ • dev_est_id  │  │ • tdd_id      │  │ • jira_story  │        │    │
│  │   │ • epic_name   │  │ • epic_id(FK) │  │ • epic_id(FK) │  │   _id         │        │    │
│  │   │ • req_desc    │  │ • dev_hours   │  │ • tdd_name    │  │ • dev_est_id  │        │    │
│  │   │ • status      │  │ • qa_hours    │  │ • tdd_desc    │  │   (FK)        │        │    │
│  │   │ • priority    │  │ • complexity  │  │ • tech_comp   │  │ • summary     │        │    │
│  │   │ • team        │  │ • risk_level  │  │ • design_dec  │  │ • story_pts   │        │    │
│  │   └───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘        │    │
│  │                                                                                      │    │
│  │                              + gitlab_code.json (code references)                    │    │
│  │                                                                                      │    │
│  └──────────────────────────────────────────────┬───────────────────────────────────────┘    │
│                                                 │                                            │
│  ┌──────────────────────────────────────────────▼───────────────────────────────────────┐    │
│  │                              STAGE 4: VECTORIZATION                                  │    │
│  │                                                                                      │    │
│  │                        ┌───────────────────────────┐                                 │    │
│  │                        │    init_vector_db.py      │                                 │    │
│  │                        │                           │                                 │    │
│  │                        │  • Load CSV/JSON files    │                                 │    │
│  │                        │  • Generate embeddings    │                                 │    │
│  │                        │    (Ollama all-minilm)    │                                 │    │
│  │                        │  • Index to ChromaDB      │                                 │    │
│  │                        └─────────────┬─────────────┘                                 │    │
│  │                                      │                                               │    │
│  │                                      ▼                                               │    │
│  │                        ┌───────────────────────────┐                                 │    │
│  │                        │       ChromaDB            │                                 │    │
│  │                        │   (Vector Store)          │                                 │    │
│  │                        │                           │                                 │    │
│  │                        │  Collections:             │                                 │    │
│  │                        │  • project_index (PRIMARY)│                                 │    │
│  │                        │    - Lightweight metadata │                                 │    │
│  │                        │    - Fast matching        │                                 │    │
│  │                        │  • epics, estimations     │                                 │    │
│  │                        │  • tdds, stories (legacy) │                                 │    │
│  │                        └───────────────────────────┘                                 │    │
│  │                                                                                      │    │
│  └──────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Pipeline Components to Build

| Stage | Component | Technology | Input | Output |
|-------|-----------|------------|-------|--------|
| 1 | Epic Extractor | python-docx | Epic DOCX files | Parsed epic data |
| 1 | Estimation Extractor | pandas/openpyxl | Excel workbooks | Parsed estimation data |
| 1 | TDD Extractor | python-docx | TDD DOCX files | Parsed TDD data |
| 1 | Story Extractor | python-docx | Story DOCX files | Parsed story data |
| 2 | Data Transformer | pandas | Parsed data | Normalized records |
| 2 | Relationship Validator | Custom | All records | Validated relationships |
| 3 | CSV/JSON Writer | pandas | Validated records | Raw data files |
| 4 | Vector Indexer | Existing script | Raw files | ChromaDB collections |

## Data Relationships (1:1:1:N)

```
EPIC/Requirement (1) ──► Estimation (1) ──► Jira Story (1) ──► GitLab Code (N)
      │                       │                  │                   │
  epic_id ◄──────────── epic_id (FK)        dev_est_id (FK)   jira_story_id (FK)
```

## Key Deliverables

1. **Document Parsers** - Python scripts to extract structured data from DOCX/Excel
2. **Data Transformation Layer** - Normalize and validate extracted data
3. **Relationship Mapper** - Link entities via foreign keys
4. **Quality Checks** - Validation rules for data integrity
5. **Incremental Update Support** - Handle new documents without full reindex

---

# SLIDE 2: Application Flow - AI Impact Assessment Pipeline

## System Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                           AI IMPACT ASSESSMENT SYSTEM                                         │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                               │
│   USER INPUT                          BACKEND (FastAPI + LangGraph)                          │
│  ┌──────────────┐                    ┌─────────────────────────────────────────────────────┐ │
│  │              │    HTTP/REST       │                                                     │ │
│  │  Frontend    │ ──────────────────►│   API Layer (FastAPI)                              │ │
│  │  (Next.js)   │                    │   • POST /api/v1/orchestrator/run                  │ │
│  │              │                    │   • Session Management                             │ │
│  │  - OR -      │◄────────────────── │   • Health Checks                                  │ │
│  │              │   JSON Response    │                                                     │ │
│  │  JSON File   │                    └───────────────────────┬─────────────────────────────┘ │
│  │  (input/)    │                                            │                               │
│  └──────────────┘                                            ▼                               │
│                                      ┌─────────────────────────────────────────────────────┐ │
│                                      │              LangGraph Workflow                      │ │
│                                      │         (Multi-Agent Orchestration)                 │ │
│                                      └───────────────────────┬─────────────────────────────┘ │
│                                                              │                               │
└──────────────────────────────────────────────────────────────┼───────────────────────────────┘
                                                               │
                                                               ▼
```

## LangGraph Agent Pipeline (Detailed Flow)

**Current Active Pipeline:** 7 agents (code_impact and risks are implemented but currently disabled)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                  LANGGRAPH WORKFLOW                                           │
│                                                                                               │
│  START                                                                                        │
│    │                                                                                          │
│    ▼                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  AGENT 1: REQUIREMENT PARSER                                                            │ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━                                                            │ │
│  │  Input:  Raw requirement text                                                           │ │
│  │  Action: Extract keywords, normalize text, identify key entities                        │ │
│  │  Output: extracted_keywords[], requirement_text                                         │ │
│  │  Status: requirement_submitted                                                          │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│    │                                                                                          │
│    ▼                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  AGENT 2: HISTORICAL MATCH                                                              │ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━                                                              │ │
│  │  Input:  Keywords + requirement text                                                    │ │
│  │  Action: Hybrid search (70% semantic + 30% keyword) across ChromaDB                     │ │
│  │          • Search project_index collection (lightweight metadata)                       │ │
│  │  Output: all_matches[] (ranked by combined score)                                       │ │
│  │  Status: matches_found                                                                  │ │
│  │                                                                                          │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────┐   │ │
│  │  │                    HYBRID SEARCH ALGORITHM                                       │   │ │
│  │  │                                                                                  │   │ │
│  │  │   Query ──► Ollama Embeddings ──► Semantic Search (ChromaDB) ──┐                │   │ │
│  │  │                                                                 │                │   │ │
│  │  │   Query ──► Keyword Extraction ──► Keyword Matching ───────────┼──► Score Fusion│   │ │
│  │  │                                                                 │                │   │ │
│  │  │   Final Score = (0.70 × Semantic) + (0.30 × Keyword)           │                │   │ │
│  │  └─────────────────────────────────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│    │                                                                                          │
│    ▼                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  AGENT 3: AUTO-SELECT + DOCUMENT LOADER                                                 │ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                                │ │
│  │  Input:  all_matches[]                                                                  │ │
│  │  Action: 1. Select top 3 matches by score (or use pre-selected matches)                │ │
│  │          2. Load FULL documents for selected projects via ContextAssembler:            │ │
│  │             • TDD document (parsed) → TDDDocument                                       │ │
│  │             • Estimation document (parsed) → EstimationDocument                         │ │
│  │             • Jira stories document (parsed) → JiraStoriesDocument                      │ │
│  │  Output: selected_matches[] (top 3) + loaded_projects{} (full documents)               │ │
│  │  Status: matches_selected                                                               │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│    │                                                                                          │
│    ▼                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  AGENT 4: IMPACTED MODULES                                                              │ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━                                                              │ │
│  │  Input:  Requirement + loaded_projects (TDD module data)                                │ │
│  │  Action: LLM analyzes to identify functional & technical modules impacted               │ │
│  │  Output: functional_modules[], technical_modules[], impact_summary                      │ │
│  │  Status: impacted_modules_generated                                                     │ │
│  │                                                                                          │ │
│  │  Context: module_list, interaction_flow, design_decisions from TDDs                     │ │
│  │  Uses: Ollama (phi3:mini) for analysis                                                  │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│    │                                                                                          │
│    ▼                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  AGENT 5: ESTIMATION EFFORT                                                             │ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━                                                             │ │
│  │  Input:  Impacted modules + historical estimations                                      │ │
│  │  Action: LLM generates effort estimates based on historical patterns                    │ │
│  │  Output: dev_hours, qa_hours, total_hours, story_points, confidence_level              │ │
│  │  Status: estimation_effort_completed                                                    │ │
│  │                                                                                          │ │
│  │  Uses: Historical estimation data for pattern matching                                  │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│    │                                                                                          │
│    ▼                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  AGENT 6: TDD GENERATOR                                                                 │ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━                                                               │ │
│  │  Input:  Requirement + modules + effort + historical TDDs                               │ │
│  │  Action: LLM generates Technical Design Document                                        │ │
│  │  Output: tdd_name, architecture_pattern, technical_components[],                       │ │
│  │          design_decisions, security_considerations, tdd.md file                         │ │
│  │  Status: tdd_generated                                                                  │ │
│  │                                                                                          │ │
│  │  Saves: Markdown TDD to sessions/{date}/{session_id}/step3_agents/agent_tdd/           │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│    │                                                                                          │
│    ▼                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  AGENT 7: JIRA STORIES                                                                  │ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━                                                               │ │
│  │  Input:  Requirement + loaded_projects (existing stories + task breakdown)              │ │
│  │  Action: LLM generates Jira user stories and sub-tasks                                  │ │
│  │  Output: stories[] with summary, description, acceptance_criteria, story_points        │ │
│  │  Status: jira_stories_generated → completed                                             │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│    │                                                                                          │
│    ▼                                                                                          │
│   END                                                                                         │
│                                                                                               │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                              FUTURE AGENTS (Currently Disabled)                               │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  CODE IMPACT AGENT  [DISABLED]                                                          │ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                                      │ │
│  │  Input:  Stories + historical code patterns                                             │ │
│  │  Action: LLM identifies files/repos likely to be impacted                               │ │
│  │  Output: impacted_files[], impacted_repos[], change_recommendations                    │ │
│  │  Status: code_impact_generated                                                          │ │
│  │                                                                                          │ │
│  │  Note: Agent implemented but disabled in workflow.py pending testing                    │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  RISKS AGENT  [DISABLED]                                                                 │ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━                                                            │ │
│  │  Input:  All previous outputs (modules, effort, TDD, stories, code impact)              │ │
│  │  Action: LLM performs risk assessment                                                   │ │
│  │  Output: risks[] with category, severity, likelihood, mitigation_strategy              │ │
│  │  Status: risks_generated                                                                │ │
│  │                                                                                          │ │
│  │  Note: Agent implemented but disabled in workflow.py pending testing                    │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                               │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

## State Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    STATE PROGRESSION                                         │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  CURRENT ACTIVE FLOW (7 agents):                                                             │
│                                                                                              │
│  created → requirement_submitted → matches_found → matches_selected                          │
│                                                          │                                   │
│                                                          ▼                                   │
│                                               impacted_modules_generated                     │
│                                                          │                                   │
│                                                          ▼                                   │
│                                               estimation_effort_completed                    │
│                                                          │                                   │
│                                                          ▼                                   │
│                                                    tdd_generated                             │
│                                                          │                                   │
│                                                          ▼                                   │
│                                            jira_stories_generated → completed                │
│                                                                                              │
│  ─────────────────────────────────────────────────────────────────────────────────────────  │
│                                                                                              │
│  FUTURE (when code_impact & risks are enabled):                                              │
│  ... → jira_stories_generated → code_impact_generated → risks_generated → completed         │
│                                                                                              │
│  ─────────────────────────────────────────────────────────────────────────────────────────  │
│                                                                                              │
│  ERROR HANDLING: Any agent can transition to "error" status → error_handler → END           │
│                                                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Infrastructure Components

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    INFRASTRUCTURE                                            │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  ┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐                  │
│  │    FastAPI        │     │    ChromaDB       │     │     Ollama        │                  │
│  │    (Port 8000)    │     │  (Vector Store)   │     │   (Local LLM)     │                  │
│  │                   │     │                   │     │                   │                  │
│  │  • REST API       │     │  • Semantic       │     │  • phi3:mini      │                  │
│  │  • Session Mgmt   │     │    Search         │     │    (Generation)   │                  │
│  │  • SSE Streaming  │     │  • Embeddings     │     │  • all-minilm     │                  │
│  │  • File Handling  │     │    Storage        │     │    (Embeddings)   │                  │
│  │  • CORS           │     │  • 5 Collections  │     │                   │                  │
│  └───────────────────┘     └───────────────────┘     └───────────────────┘                  │
│           │                         │                         │                             │
│           └─────────────────────────┼─────────────────────────┘                             │
│                                     │                                                        │
│                                     ▼                                                        │
│                         ┌───────────────────────┐                                           │
│                         │   LangGraph Engine    │                                           │
│                         │                       │                                           │
│                         │  • State Management   │                                           │
│                         │  • Agent Routing      │                                           │
│                         │  • Error Recovery     │                                           │
│                         │  • Streaming Support  │                                           │
│                         └───────────────────────┘                                           │
│                                                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Real-Time Streaming (SSE)

The system supports Server-Sent Events for real-time progress updates:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SSE STREAMING ARCHITECTURE                                      │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│   Frontend                                 Backend                                           │
│   ┌─────────────┐                         ┌─────────────────────────────────────────────┐   │
│   │             │  GET /orchestrator/     │                                             │   │
│   │  EventSource│  run-stream             │   LangGraph Workflow                        │   │
│   │             │ ─────────────────────►  │                                             │   │
│   │             │                         │   ┌─────────┐  ┌─────────┐  ┌─────────┐    │   │
│   │             │  event: pipeline_start  │   │ Agent 1 │→ │ Agent 2 │→ │ Agent N │    │   │
│   │             │ ◄─────────────────────  │   └────┬────┘  └────┬────┘  └────┬────┘    │   │
│   │             │                         │        │            │            │          │   │
│   │             │  event: agent_complete  │        └────────────┴────────────┘          │   │
│   │             │ ◄─────────────────────  │              SSE Events                     │   │
│   │             │                         │                                             │   │
│   │             │  event: agent_complete  │   Event Types:                              │   │
│   │             │ ◄─────────────────────  │   • pipeline_start (0%)                     │   │
│   │             │         ...             │   • agent_complete (progress %)             │   │
│   │             │                         │   • pipeline_complete (100%)                │   │
│   │             │  event: pipeline_done   │   • pipeline_error (on failure)             │   │
│   │             │ ◄─────────────────────  │                                             │   │
│   └─────────────┘                         └─────────────────────────────────────────────┘   │
│                                                                                              │
│   Event Payload Example:                                                                     │
│   {                                                                                          │
│     "event": "agent_complete",                                                               │
│     "agent": "tdd",                                                                          │
│     "status": "success",                                                                     │
│     "progress": 71,                                                                          │
│     "message": "TDD generated successfully"                                                  │
│   }                                                                                          │
│                                                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Output Artifacts (Per Session)

```
sessions/{date}/{session_id}/
│
├── step1_input/
│   ├── requirement.json          # Original input
│   └── extracted_keywords.json   # Parsed keywords
│
├── step2_historical_match/
│   ├── search_request.json       # Search parameters
│   ├── all_matches.json          # Full search results
│   └── selected_matches.json     # Top 5 selected
│
├── step3_agents/
│   ├── agent_impacted_modules/
│   │   ├── input_prompt.txt      # LLM prompt
│   │   ├── raw_response.txt      # LLM raw output
│   │   └── parsed_output.json    # Structured output
│   ├── agent_estimation_effort/
│   │   └── ...                   # Same structure
│   ├── agent_tdd/
│   │   ├── input_prompt.txt      # LLM prompt
│   │   ├── raw_response.txt      # LLM raw output
│   │   ├── tdd.md                # Generated TDD document
│   │   └── parsed_output.json    # Structured output
│   ├── agent_jira_stories/
│   │   └── ...                   # Same structure
│   ├── agent_code_impact/        # (future - currently disabled)
│   └── agent_risks/              # (future - currently disabled)
│
└── final_summary.json            # Complete assessment
```

---

## Summary

| Aspect | Details |
|--------|---------|
| **Input** | New requirement description (text or JSON file) |
| **Processing** | 7 active agents in sequence (2 additional agents pending) |
| **AI Engine** | Ollama (local) - phi3:mini + all-minilm |
| **Search** | Hybrid (70% semantic + 30% keyword) via ChromaDB project_index |
| **Context** | Full documents loaded for top 3 matching projects |
| **Output** | TDD, Effort Estimate, Jira Stories |
| **Traceability** | Full audit trail saved per session |
| **Real-time Updates** | Server-Sent Events (SSE) for live progress streaming |

---

## Value Proposition

1. **Faster Impact Analysis** - Automated instead of manual research
2. **Consistent Estimations** - Based on historical patterns
3. **Comprehensive TDDs** - AI-generated technical designs
4. **Ready-to-Use Stories** - Jira-ready user stories
5. **Real-Time Visibility** - Live progress streaming via SSE
6. **Full Traceability** - Audit trail for compliance

## Roadmap

| Feature | Status | Notes |
|---------|--------|-------|
| Requirement Parsing | ✅ Active | Keyword extraction |
| Historical Matching | ✅ Active | Hybrid search via project_index |
| Auto-Select + Doc Loading | ✅ Active | Top 3 matches + full document loading |
| Impacted Modules | ✅ Active | LLM analysis with TDD context |
| Effort Estimation | ✅ Active | Historical pattern matching |
| TDD Generation | ✅ Active | Markdown output |
| Jira Stories | ✅ Active | Story + task generation |
| Code Impact Analysis | 🔜 Pending | Implemented, testing |
| Risk Assessment | 🔜 Pending | Implemented, testing |

---

*Document Version: 2.0*
*Last Updated: January 2026*
