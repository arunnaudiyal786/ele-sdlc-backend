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
│  │                        │  • epics                  │                                 │    │
│  │                        │  • estimations            │                                 │    │
│  │                        │  • tdds                   │                                 │    │
│  │                        │  • stories                │                                 │    │
│  │                        │  • gitlab_code            │                                 │    │
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
│  │          • Search epics, estimations, tdds, stories collections                         │ │
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
│  │  AGENT 3: AUTO-SELECT                                                                   │ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━                                                                │ │
│  │  Input:  all_matches[]                                                                  │ │
│  │  Action: Select top 5 matches by score (or use pre-selected matches)                   │ │
│  │  Output: selected_matches[] (top 5)                                                     │ │
│  │  Status: matches_selected                                                               │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│    │                                                                                          │
│    ▼                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  AGENT 4: IMPACTED MODULES                                                              │ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━                                                              │ │
│  │  Input:  Requirement + selected matches                                                 │ │
│  │  Action: LLM analyzes to identify functional & technical modules impacted               │ │
│  │  Output: functional_modules[], technical_modules[], impact_summary                      │ │
│  │  Status: impacted_modules_generated                                                     │ │
│  │                                                                                          │ │
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
│  │  Input:  Requirement + TDD + modules                                                    │ │
│  │  Action: LLM generates Jira user stories and sub-tasks                                  │ │
│  │  Output: stories[] with summary, description, acceptance_criteria, story_points        │ │
│  │  Status: jira_stories_generated                                                         │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│    │                                                                                          │
│    ▼                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  AGENT 8: CODE IMPACT                                                                   │ │
│  │  ━━━━━━━━━━━━━━━━━━━━━━                                                                │ │
│  │  Input:  Stories + historical code patterns                                             │ │
│  │  Action: LLM identifies files/repos likely to be impacted                               │ │
│  │  Output: impacted_files[], impacted_repos[], change_recommendations                    │ │
│  │  Status: code_impact_generated                                                          │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│    │                                                                                          │
│    ▼                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  AGENT 9: RISKS                                                                         │ │
│  │  ━━━━━━━━━━━━━━━━                                                                      │ │
│  │  Input:  All previous outputs (modules, effort, TDD, stories, code impact)              │ │
│  │  Action: LLM performs risk assessment                                                   │ │
│  │  Output: risks[] with category, severity, likelihood, mitigation_strategy              │ │
│  │  Status: risks_generated → completed                                                    │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘ │
│    │                                                                                          │
│    ▼                                                                                          │
│   END                                                                                         │
│                                                                                               │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

## State Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    STATE PROGRESSION                                         │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  created → requirement_submitted → matches_found → matches_selected                          │
│                                                          │                                   │
│                                                          ▼                                   │
│  completed ← risks_generated ← code_impact_generated ← jira_stories_generated               │
│                                                          ▲                                   │
│                                                          │                                   │
│            tdd_generated ← estimation_effort_completed ← impacted_modules_generated         │
│                                                                                              │
│  Error Handling: Any agent can transition to "error" status → error_handler → END           │
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
│  │  • File Handling  │     │  • Embeddings     │     │  • all-minilm     │                  │
│  │  • CORS           │     │    Storage        │     │    (Embeddings)   │                  │
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
│                         └───────────────────────┘                                           │
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
├── step2_search/
│   ├── search_request.json       # Search parameters
│   ├── all_matches.json          # Full search results
│   └── selected_matches.json     # Top 5 selected
│
├── step3_agents/
│   ├── agent_impacted_modules/
│   ├── agent_estimation_effort/
│   ├── agent_tdd/
│   │   ├── input_prompt.txt      # LLM prompt
│   │   ├── raw_response.txt      # LLM raw output
│   │   ├── tdd.md                # Generated TDD document
│   │   └── parsed_output.json    # Structured output
│   ├── agent_jira_stories/
│   ├── agent_code_impact/
│   └── agent_risks/
│
└── final_summary.json            # Complete assessment
```

---

## Summary

| Aspect | Details |
|--------|---------|
| **Input** | New requirement description (text or JSON file) |
| **Processing** | 9 specialized AI agents in sequence |
| **AI Engine** | Ollama (local) - phi3:mini + all-minilm |
| **Search** | Hybrid (70% semantic + 30% keyword) via ChromaDB |
| **Output** | TDD, Effort Estimate, Jira Stories, Code Impact, Risks |
| **Traceability** | Full audit trail saved per session |

---

## Value Proposition

1. **Faster Impact Analysis** - Automated instead of manual research
2. **Consistent Estimations** - Based on historical patterns
3. **Comprehensive TDDs** - AI-generated technical designs
4. **Ready-to-Use Stories** - Jira-ready user stories
5. **Risk Visibility** - Proactive risk identification
6. **Full Traceability** - Audit trail for compliance

---

*Document Version: 1.0*
*Last Updated: January 2026*
