# AI-Powered Impact Assessment System
## Data Model & Architecture Design Document

---

## Executive Summary

This document presents the data architecture for an AI-powered impact assessment system that analyzes incoming project requirements and automatically identifies impacted functional and technical modules. The system leverages multi-agent AI with Retrieval-Augmented Generation (RAG) to enable accurate project planning and effort estimation.

**Key Design Decision:** TDD is embedded as a technical component INSIDE Dev/QA Estimation. One TDD maps to one technical component inside the estimation.

---

## 1. Current Data Landscape

### 1.1 Data Source Overview

| Data Source | Format | Records | Primary Purpose |
|-------------|--------|---------|-----------------|
| Project Requirements | .txt | 1 document | Input specifications for analysis |
| Dev Estimation (with TDD) | .csv | 14 tasks | Development effort baseline + Technical Design |
| QA Estimation | .csv | 14 scenarios | Testing effort baseline |
| Jira Tickets | .csv | 5 stories | Historical execution patterns |

### 1.2 Current Data Structure Analysis

**Dev Estimation with TDD (dev_estimation.csv)**

| Domain | Tasks | Total Effort (Hrs) | Avg Complexity |
|--------|-------|-------------------|----------------|
| Renewals | 4 | 470 | Large/Medium |
| Plan Changes | 3 | 244 | Medium |
| Riders | 2 | 168 | Medium |
| Integration | 4 | 353 | Large/Medium |
| Configuration | 1 | 42 | Small |
| **Total** | **14** | **1,277** | - |

---

## 2. Proposed Data Model

### 2.1 Data Structure: For Impact Evaluation & TDD Support Use Case

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                    DATA MAPPING & CONSOLIDATION                                   │
│              For Impact Evaluation & TDD Support Use Case                         │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  POC Entry                                                                        │
│    Point                                                                          │
│      │                                                                            │
│      ▼                                                                            │
│  ┌────────┐      ┌─────────────────────────────┐      ┌────────┐      ┌────────┐ │
│  │   1    │ 1:1  │            2                │ 1:1  │   3    │ 1:N  │   4    │ │
│  │  EPIC/ │─────►│       Dev/QA Est            │─────►│  Jira  │─────►│ Gitlab │ │
│  │  Req   │      │  ┌───────────────────────┐  │      │ Story/ │      │ Repo/  │ │
│  │        │      │  │  TDD (Technical       │  │      │ Tasks  │      │ Files  │ │
│  │        │      │  │  Component - embedded)│  │      │        │      │        │ │
│  └────────┘      │  └───────────────────────┘  │      └────────┘      └────────┘ │
│                  └─────────────────────────────┘                                  │
│                                                                                   │
│  Note: TDD is a technical component INSIDE Dev/QA Estimation (not separate)      │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Relationship Cardinality Summary

| From Entity | Relationship | To Entity | Description |
|-------------|--------------|-----------|-------------|
| EPIC/Requirements | 1:1 | Dev/QA Estimation (with TDD) | One EPIC maps to one Estimation containing TDD |
| Dev/QA Estimation | 1:1 | Jira Story/Tasks | One Estimation maps to one Story |
| Jira Story/Tasks | 1:N | Gitlab Repo/Files | One Story impacts multiple files |

**Note:** TDD is embedded as a technical component within Estimation, not a separate entity.

---

### 2.3 Detailed Entity Descriptions

#### STEP 1: EPIC/Requirements (POC Entry Point)

**CURRENT DATA SOURCE:**
- EPIC created by user in Jira along with requirement detail in Jira ticket description
- Ex: MM16783

**AI VALUE ADD:**
- AI will retrieve the historical requirements based on the new requirement

**ATTRIBUTES:**
| Attribute | Type | Description |
|-----------|------|-------------|
| epic_id | PK | Primary key identifier |
| epic_name | VARCHAR | Human-readable name |
| req_id | VARCHAR | Requirement identifier |
| jira_id | VARCHAR | Jira EPIC identifier |
| req_description | TEXT | Detailed requirement description |
| status | ENUM | Current status |

---

#### STEP 2: Dev/QA Estimation (Contains TDD as Technical Component)

**CURRENT DATA SOURCE:**
- Estimation template created by user with technical/functional module mapping
- TDD is present in each Jira EPIC (Ex: Milestone-TDD task in Jira)

**BUSINESS NEED:**
- Identification of impacted technical/functional modules
- Recommending baseline effort patterns from historical data
- Documents components and dependencies (via embedded TDD)

**AI VALUE ADD:**
- AI will recommend estimations based on historical data
- AI will recommend historical TDDs related to the requirement
- AI will identify technical/functional modules that will be impacted

**ATTRIBUTES:**

*Estimation Fields:*
| Attribute | Type | Description |
|-----------|------|-------------|
| dev_est_id | PK | Primary key identifier |
| epic_id | FK | Foreign key to epic_requirements (UNIQUE - 1:1) |
| module_id | VARCHAR | Module identifier |
| task_description | TEXT | Detailed task description |
| complexity | ENUM | Small / Medium / Large |
| dev_effort_hours | DECIMAL | Development effort hours |
| qa_effort_hours | DECIMAL | QA effort hours |
| total_effort_hours | DECIMAL | Total effort hours |

*TDD Fields (Technical Component - Embedded):*
| Attribute | Type | Description |
|-----------|------|-------------|
| tdd_id | VARCHAR | TDD identifier |
| tdd_name | VARCHAR | Technical Design Document name |
| tdd_description | TEXT | Detailed TDD description |
| technical_components | TEXT[] | Array of technologies/components |
| design_decisions | TEXT | Key design decisions |
| tdd_dependencies | TEXT[] | Service dependencies |
| tdd_status | ENUM | Draft / In Review / Approved |

---

#### STEP 3: Jira Story/Tasks

**CURRENT DATA SOURCE:**
- Jira tickets are mapped for each EPIC in the dashboard
- Ex: MMO-12323

**AI VALUE ADD:**
- AI will create respective Jira User Story and Tasks

**ATTRIBUTES:**
| Attribute | Type | Description |
|-----------|------|-------------|
| jira_story_id | PK | Primary key identifier |
| dev_est_id | FK | Foreign key to dev_qa_estimation (1:1) |
| issue_type | ENUM | Story / Task / Sub-task / Bug |
| summary | VARCHAR | Task/story summary |
| assignee | VARCHAR | Assigned developer |
| status | ENUM | Current status |
| story_points | DECIMAL | Effort estimate |
| sprint | VARCHAR | Sprint identifier |

---

#### STEP 4: Gitlab Repo/Files

**CURRENT DATA SOURCE:**
- CHG request has JIRA tickets mapped
- Each .cbl file has change details

**AI VALUE ADD:**
- AI will recommend which files will be impacted based on the previous steps

**ATTRIBUTES:**
| Attribute | Type | Description |
|-----------|------|-------------|
| chg_id | PK | Primary key identifier |
| jira_story_id | FK | Foreign key to jira_story_tasks |
| file_path | VARCHAR | File path in repository |
| change_type | ENUM | New / Modified / Deleted |
| change_details | TEXT | Description of changes |

---

### 2.4 Complete Traceability Chain

```
EPIC/REQUIREMENTS: MM16783 (FOA Large Group Renewals) [POC ENTRY POINT]
│
│ • Epic_id: EPIC-001
│ • Epic_name: FOA Large Group Renewals Enhancement
│ • Req_description: GSF Excel Template Automation
│
└──► DEV/QA ESTIMATION: GB960 (with TDD as Technical Component)
    │
    │ Estimation Fields:
    │ • Dev_est_id: EST-001
    │ • Task_description: Build GSF Template Generator
    │ • Complexity: Large | Total Effort: 155 hrs
    │
    │ TDD Fields (Technical Component - Embedded):
    │ • TDD_id: TDD-001
    │ • TDD_name: GSF Template Technical Design
    │ • Technical_components: [Excel Gen, Kafka, DB]
    │ • Design_decisions: Use Kafka for async processing
    │ • TDD_dependencies: [SORD Integration, COM2]
    │
    └──► JIRA STORY: MMO-12323 (Design GSF Structure)
        │ • Issue_type: Story
        │ • Summary: Design GSF template structure
        │
        ├──► GITLAB: CHG-12345
        │    • File: /src/gsf/template_generator.cbl
        │    • Change_type: Modified
        │
        └──► GITLAB: CHG-12346
             • File: /src/gsf/excel_writer.cbl
             • Change_type: New

SUMMARY:
• EPIC/Requirements ──► 1 Dev/QA Estimation with embedded TDD (1:1)
• Dev/QA Estimation ──► 1 Jira Story/Task (1:1)
• Jira Story/Task ──► Multiple Gitlab Files (1:N)

KEY: TDD is embedded within Estimation as a technical component
```

---

### 2.5 Database Schema Definition

```sql
-- STEP 1: EPIC/Requirements Layer - POC ENTRY POINT
CREATE TABLE epic_requirements (
    epic_id VARCHAR(50) PRIMARY KEY,
    epic_name VARCHAR(255) NOT NULL,
    req_id VARCHAR(50),
    jira_id VARCHAR(50),
    req_description TEXT NOT NULL,
    status VARCHAR(50),
    embedding_vector VECTOR(1536),
    created_date TIMESTAMP
);

-- STEP 2: Dev/QA Estimation with TDD as Technical Component (1:1 from EPIC)
CREATE TABLE dev_qa_estimation (
    dev_est_id VARCHAR(50) PRIMARY KEY,
    epic_id VARCHAR(50) UNIQUE REFERENCES epic_requirements(epic_id),
    
    -- Estimation Fields
    module_id VARCHAR(50),
    task_description TEXT,
    complexity VARCHAR(20) CHECK (complexity IN ('Small','Medium','Large')),
    dev_effort_hours DECIMAL(10,2),
    qa_effort_hours DECIMAL(10,2),
    total_effort_hours DECIMAL(10,2),
    
    -- TDD Fields (Technical Component - Embedded)
    tdd_id VARCHAR(50),
    tdd_name VARCHAR(255),
    tdd_description TEXT,
    technical_components TEXT[],
    design_decisions TEXT,
    tdd_version VARCHAR(20),
    tdd_status VARCHAR(50),
    tdd_author VARCHAR(100),
    tdd_dependencies TEXT[],
    
    other_params JSONB
);

-- STEP 3: Jira Story/Tasks Layer (1:1 from Estimation)
CREATE TABLE jira_story_tasks (
    jira_story_id VARCHAR(50) PRIMARY KEY,
    dev_est_id VARCHAR(50) UNIQUE REFERENCES dev_qa_estimation(dev_est_id),
    issue_type VARCHAR(50),
    summary VARCHAR(500),
    description TEXT,
    assignee VARCHAR(100),
    status VARCHAR(50),
    story_points DECIMAL(10,2),
    sprint VARCHAR(50),
    other_params JSONB
);

-- STEP 4: Gitlab Repo/Files Layer (1:N from Jira Story/Tasks)
CREATE TABLE gitlab_repo_files (
    chg_id VARCHAR(50) PRIMARY KEY,
    jira_story_id VARCHAR(50) REFERENCES jira_story_tasks(jira_story_id),
    cab_id VARCHAR(50),
    file_path VARCHAR(500),
    change_type VARCHAR(50) CHECK (change_type IN ('New','Modified','Deleted')),
    change_details TEXT,
    status VARCHAR(50),
    created_date TIMESTAMP
);
```

---

### 2.6 Knowledge Graph Schema (Neo4j)

```cypher
// Node Types (4-Step Model - TDD embedded in Estimation)
(:EpicRequirements {epic_id, epic_name, req_id, jira_id, req_description, status})

(:DevQAEstimationWithTDD {
    dev_est_id, epic_id, module_id, task_description, complexity,
    dev_effort_hours, qa_effort_hours, total_effort_hours,
    tdd_id, tdd_name, tdd_description, technical_components, 
    design_decisions, tdd_dependencies, tdd_status
})

(:JiraStoryTasks {jira_story_id, dev_est_id, issue_type, summary, status})
(:GitlabRepoFiles {chg_id, jira_story_id, file_path, change_type})

// Relationships
(:EpicRequirements)-[:HAS_ESTIMATION_WITH_TDD {1:1}]->(:DevQAEstimationWithTDD)
(:DevQAEstimationWithTDD)-[:HAS_STORY {1:1}]->(:JiraStoryTasks)
(:JiraStoryTasks)-[:IMPACTS_FILES {1:N}]->(:GitlabRepoFiles)
```

---

### 2.7 One-Liner Descriptions & AI Value Add

| Step | Entity | Description | AI Value Add |
|------|--------|-------------|--------------|
| 1 | EPIC/Requirements | EPIC with requirement details (POC Entry Point) | Retrieve historical requirements |
| 2 | Dev/QA Estimation (with TDD) | Estimation with TDD as technical component | Recommend estimations with TDD and impacted modules |
| 3 | Jira Story/Tasks | Jira tickets mapped for each EPIC | Create Jira User Stories and Tasks |
| 4 | Gitlab Repo/Files | CHG requests with file mappings | Recommend impacted files |

---

## 3. RAG Query Pipeline

```
NEW REQUIREMENT
"Add support for Dental product in Group Structure automation"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Query Embedding                                          │
│ embed("Add support for Dental product...") → [0.045, -0.234, ...]│
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Multi-Collection Search                                  │
│                                                                   │
│ Estimation+TDD Collection:                                        │
│   → Match: "Group Structure Automation - Enhance for D/V data"   │
│   → TDD Components: [Excel Gen, Kafka, DB]                       │
│   → TDD Dependencies: [SORD Integration]                         │
│   → Effort: 125 hrs, Complexity: Large                           │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: LLM Generation - Impact Assessment Report                │
│                                                                   │
│ {                                                                 │
│   "functional_modules": [...],                                    │
│   "technical_modules": [...],                                     │
│   "tdd_components": ["Excel Gen", "Kafka", "DB"],                │
│   "total_effort": {"dev": 125, "qa": 65.7, "total": 190.7},     │
│   "dependencies": ["SORD Integration"],                          │
│   "confidence": 0.87                                              │
│ }                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Summary

### Data Source Value Matrix

| Data Source | Primary Value | RAG Contribution |
|-------------|---------------|------------------|
| Project Requirements | Semantic Understanding | Query embedding source |
| Dev Estimation (with TDD) | Effort Baseline + Tech Architecture | Historical patterns + Component matching |
| QA Estimation | Quality Planning | QA effort ratios |
| Jira Tickets | Execution Intelligence | Subtask patterns |

### Key Architecture Decision

TDD is embedded as a technical component within Dev/QA Estimation. This design:
- Simplifies the data model to 4 steps instead of 5
- Maintains 1:1 mapping between TDD and technical component
- Keeps estimation and technical design information together
- Enables combined embeddings for better semantic matching

---

**Document Version:** 2.1  
**Updated:** December 2025  
**Author:** AI Data Architecture Team
