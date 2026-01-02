# Enterprise Knowledge Base - Data Schema Documentation

## Overview

This document describes the synthetic data schema designed to enable AI agents to answer questions about software development projects by traversing relationships between Epics/Requirements, Dev/QA Estimations (with TDD as technical component), Jira Stories/Tasks, and GitLab Repo/Files.

The data follows a hierarchical structure that mirrors real-world enterprise software development workflows, enabling semantic search, relationship traversal, and contextual question answering for impact evaluation and TDD support.

---

## Data Architecture

**Discovery: For Impact Evaluation & TDD Support Use Case**

End-to-end traceability from Jira Align through Jira tickets, providing the structural foundation for accurate pattern matching and effort prediction.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DATA MAPPING & CONSOLIDATION                          │
│            For Impact Evaluation & TDD Support Use Case                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  POC Entry                                                               │
│    Point                                                                 │
│      │                                                                   │
│      ▼                                                                   │
│  ┌────────┐      ┌─────────────────────────┐      ┌────────┐      ┌────────┐
│  │   1    │ 1:1  │          2              │ 1:1  │   3    │ 1:N  │   4    │
│  │  EPIC/ │─────►│     Dev/QA Est          │─────►│  Jira  │─────►│ Gitlab │
│  │  Req   │      │  ┌─────────────────┐    │      │ Story/ │      │ Repo/  │
│  │        │      │  │ TDD (Technical  │    │      │ Tasks  │      │ Files  │
│  │        │      │  │   Component)    │    │      │        │      │        │
│  └────────┘      │  └─────────────────┘    │      └────────┘      └────────┘
│                  └─────────────────────────┘                              │
│                                                                          │
│  Note: TDD is a technical component INSIDE Dev/QA Estimation             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Relationship Cardinality Summary

| From Entity | Relationship | To Entity |
|-------------|--------------|-----------|
| EPIC/Requirements | 1:1 | Dev/QA Estimation (contains TDD) |
| Dev/QA Estimation | 1:1 | Jira Story/Tasks |
| Jira Story/Tasks | 1:N | Gitlab Repo/Files |

**Note:** TDD is embedded as a technical component within the Dev/QA Estimation entity. One TDD maps to one technical component inside the estimation.

---

## File Descriptions

### 1. epics.csv (STEP 1 - POC Entry Point)

**Purpose:** Master reference for all major project initiatives - serves as the single source of truth for project scope

**Business Need:**
- The EPIC/Requirements serves as the single source of truth for project scope
- Enables AI to retrieve and match historical requirements for accurate impact prediction

**AI Value Add:**
- AI will retrieve the historical requirements based on the new requirement

**Importance for AI Agents:**
- Serves as the **root entity** and POC entry point for all queries
- Provides high-level context about project goals, timelines, and ownership
- Enables filtering by team, priority, status, and date ranges
- Essential for answering questions like:
  - "What are all the critical priority projects?"
  - "Which projects is the Platform team working on?"
  - "What projects are scheduled to complete in Q2?"

**Schema:**

| Field | Type | Description | AI Search Relevance |
|-------|------|-------------|---------------------|
| `epic_id` | String | Primary key (e.g., EPIC-001) | Exact match lookups |
| `epic_name` | String | Human-readable name | Semantic search, keyword matching |
| `req_id` | String | Requirement identifier | Exact match lookups |
| `jira_id` | String | Jira EPIC identifier (e.g., MM16783) | System integration |
| `req_description` | Text | Detailed description of the requirement | Semantic search, context retrieval |
| `status` | Enum | Planning, In Progress, Done, Blocked | Filtering |
| `epic_priority` | Enum | Critical, High, Medium, Low | Filtering, ranking |
| `epic_owner` | String | Email of responsible person | Entity resolution |
| `epic_team` | String | Owning team name | Filtering, aggregation |
| `epic_start_date` | Date | Planned start date | Temporal queries |
| `epic_target_date` | Date | Target completion date | Temporal queries |
| `created_at` | Timestamp | Record creation time | Audit, versioning |
| `updated_at` | Timestamp | Last modification time | Change tracking |

**Sample Queries Enabled:**
- "Show me all in-progress projects for the Commerce team"
- "What critical projects are at risk of missing their deadline?"
- "Find historical requirements similar to this new requirement"

---

### 2. estimations.csv (STEP 2 - Contains TDD as Technical Component)

**Purpose:** Development and QA effort estimates linked to each Epic (1:1 relationship), with TDD embedded as a technical component

**Business Need:**
- Identification of impacted technical/functional modules
- Recommending baseline effort patterns from historical data
- Documents components and dependencies (via TDD)
- Identifies technical impact areas early in the project lifecycle

**AI Value Add:**
- AI will recommend estimations based on historical estimations to aid in the initial draft of the dev/qa/arch estimation template
- AI will identify technical/functional modules that will be impacted
- AI will recommend historical TDDs related to the requirement

**Importance for AI Agents:**
- Provides **resource planning context** for project decisions
- Enables capacity and workload analysis
- Links effort to complexity and risk assessments
- Contains technical design information (TDD) for architecture details
- Essential for answering questions like:
  - "How many developer hours are allocated to the Payment Gateway?"
  - "Which projects have the highest risk level?"
  - "What's the total QA effort across all Commerce projects?"
  - "What technologies does the Order Management system use?"
  - "Which services depend on the auth-service?"

**Schema:**

| Field | Type | Description | AI Search Relevance |
|-------|------|-------------|---------------------|
| `dev_est_id` | String | Primary key (e.g., EST-001) | Exact match lookups |
| `epic_id` | String | Foreign key to epics.csv (UNIQUE - 1:1) | Relationship traversal |
| `module_id` | String | Module identifier | Module tracking |
| `task_description` | Text | Detailed task description | Semantic search |
| `complexity` | Enum | Small, Medium, Large | Filtering, risk analysis |
| `dev_effort_hours` | Decimal | Estimated development hours | Aggregation, comparison |
| `qa_effort_hours` | Decimal | Estimated QA/testing hours | Aggregation, comparison |
| `total_effort_hours` | Decimal | Combined effort hours | Aggregation |
| `total_story_points` | Integer | Agile story points sum | Velocity calculations |
| `risk_level` | Enum | Low, Medium, High | Filtering, prioritization |
| `estimation_method` | String | Planning Poker, T-Shirt, etc. | Context |
| `confidence_level` | Enum | Low, Medium, High | Reliability assessment |
| `estimated_by` | String | Person who created estimate | Accountability |
| `estimation_date` | Date | When estimate was made | Temporal context |
| **TDD Fields (Technical Component)** | | | |
| `tdd_id` | String | TDD identifier (e.g., TDD-001) | Exact match lookups |
| `tdd_name` | String | Technical Design Document name | Semantic search |
| `tdd_description` | Text | Detailed TDD description | Semantic search, RAG |
| `technical_components` | Array | Technologies/components used | Technology search |
| `design_decisions` | Text | Key design decisions | Semantic search |
| `tdd_version` | String | Version number | Version filtering |
| `tdd_status` | Enum | Draft, In Review, Approved | Filtering |
| `tdd_author` | String | Document author email | Entity resolution |
| `tdd_dependencies` | Array | Service dependencies | Impact analysis |
| `other_params` | JSONB | Additional parameters | Flexible metadata |

**Sample Queries Enabled:**
- "What's the total development effort for Q1 projects?"
- "Which high-complexity projects have low confidence estimates?"
- "Compare dev vs QA hours across all epics"
- "Recommend effort estimates based on similar historical tasks"
- "What's the security architecture for the payment gateway?"
- "Which projects use Kafka?"
- "Find TDDs similar to this requirement"

---

### 3. stories_tasks.csv (STEP 3)

**Purpose:** Jira-style work items linked to Dev/QA Estimations (1:1 from Estimation)

**Business Need:**
- Granular execution tracking at task level
- Links estimations to trackable deliverables

**AI Value Add:**
- AI will create respective Jira User Story and Tasks

**Importance for AI Agents:**
- Provides **granular work breakdown** for each project
- Links implementation tasks to specific estimations and their TDD components
- Enables progress tracking and sprint analysis
- Essential for answering questions like:
  - "What stories are assigned to Sprint-25?"
  - "Which tasks implement the Security section of the auth TDD?"
  - "What's the status of all payment-related stories?"

**Schema:**

| Field | Type | Description | AI Search Relevance |
|-------|------|-------------|---------------------|
| `jira_story_id` | String | Primary key (e.g., MMO-12323) | Exact match lookups |
| `dev_est_id` | String | Foreign key to estimations.csv (1:1) | Estimation linkage |
| `issue_type` | Enum | Story, Task, Sub-task, Bug | Filtering |
| `summary` | String | Task/story summary | Semantic search |
| `description` | Text | Detailed description | Semantic search |
| `assignee` | String | Assigned developer email | Workload analysis |
| `status` | Enum | To Do, In Progress, Done | Progress tracking |
| `story_points` | Decimal | Effort estimate | Velocity, aggregation |
| `sprint` | String | Sprint identifier | Sprint filtering |
| `priority` | Enum | High, Medium, Low | Prioritization |
| `labels` | Array | Tags (comma-separated) | Categorical filtering |
| `story_created_date` | Date | Creation date | Temporal queries |
| `story_updated_date` | Date | Last update | Change tracking |
| `other_params` | JSONB | Additional parameters | Flexible metadata |

**Sample Queries Enabled:**
- "What features are in Sprint-26?"
- "Show me all blocked tasks for the mobile backend"
- "Which developer has the most story points assigned?"
- "List all security-labeled tasks across projects"

---

### 4. gitlab_code.json (STEP 4)

**Purpose:** GitLab code references linked to stories (1:N from Story/Task)

**Business Need:**
- Enables requirement to code traceability
- Reduces manual impact analysis effort at repo level

**AI Value Add:**
- AI will recommend which files will be impacted or needs to be updated based on the previous steps

**Importance for AI Agents:**
- Provides **direct code traceability** from requirements to implementation
- Enables code-level question answering
- Links commits, branches, and merge requests to work items
- Essential for answering questions like:
  - "What code implements the JWT authentication?"
  - "Which files were changed for the payment integration?"
  - "What's the code coverage for the order service?"

**Schema:**

| Field | Type | Description | AI Search Relevance |
|-------|------|-------------|---------------------|
| `chg_id` | String | Primary key (e.g., CHG-12345) | Exact match |
| `jira_story_id` | String | Foreign key to stories_tasks.csv | Work item linkage |
| `cab_id` | String | Change Advisory Board identifier | Change management |
| `file_path` | String | File path in repository | File-level queries |
| `change_type` | Enum | New, Modified, Deleted | Change tracking |
| `change_details` | Text | Description of changes | Semantic search |
| `gitlab_repo` | String | Repository path | Repository filtering |
| `gitlab_branch` | String | Feature branch name | Branch tracking |
| `gitlab_commit_sha` | String | Commit hash | Version pinning |
| `gitlab_merge_request` | String | MR identifier | Review tracking |
| `gitlab_mr_status` | Enum | merged, open, not_started | Progress filtering |
| `code_block_description` | String | What the code does | Semantic search |
| `lines_of_code` | Integer | LOC count | Metrics |
| `code_language` | String | Programming language | Language filtering |
| `functions_defined` | Array | Function names | Code search |
| `classes_defined` | Array | Class names | Code search |
| `tables_created` | Array | Database tables (for SQL) | Schema queries |
| `test_cases` | Integer | Number of test cases | Quality metrics |
| `last_commit_date` | Timestamp | Latest commit time | Freshness |
| `code_reviewer` | String | Reviewer email | Review tracking |
| `code_coverage` | Float | Test coverage percentage | Quality metrics |
| `status` | Enum | Active, Archived | Status filtering |

**Sample Queries Enabled:**
- "What code implements the password reset feature?"
- "Show me all Python files in the payment service"
- "Which merge requests are still open?"
- "What's the average code coverage across all services?"
- "Which files will be impacted by this requirement?"

---

## Relationship Mapping Reference

### Primary Key → Foreign Key Relationships

```
epics.csv (STEP 1 - POC Entry Point)
└── epic_id (PK)
    └── estimations.csv.epic_id (FK) [1:1]

estimations.csv (STEP 2 - Contains TDD as Technical Component)
└── dev_est_id (PK)
    ├── tdd_id (embedded - TDD is a technical component within estimation)
    └── stories_tasks.csv.dev_est_id (FK) [1:1]

stories_tasks.csv (STEP 3)
└── jira_story_id (PK)
    └── gitlab_code.json.jira_story_id (FK) [1:N]
```

### Cross-Reference Query Examples

| Query Type | Files Involved | Join Path |
|------------|---------------|-----------|
| "Get all code for an Epic" | epics → estimations → stories → gitlab_code | Full chain traversal |
| "Get TDD for code" | gitlab_code → stories → estimations (tdd_* fields) | jira_story_id → dev_est_id |
| "Get estimation for a story" | stories → estimations | dev_est_id |
| "Get all files for a TDD" | estimations → stories → gitlab_code | dev_est_id → jira_story_id |

---

## AI Agent Usage Patterns

### Pattern 1: Hierarchical Context Retrieval

When a user asks about code, retrieve the full context chain:

```
Code Block → Story → Estimation (with TDD) → Epic
```

**Example:** "Explain the JWT implementation"
1. Search `gitlab_code.json` for JWT-related code
2. Get linked `jira_story_id` → retrieve story context
3. Get linked `dev_est_id` → retrieve estimation details AND TDD technical component
4. Get linked `epic_id` → retrieve project goals
5. Synthesize comprehensive answer

### Pattern 2: Impact Analysis

When analyzing changes, traverse the hierarchy:

```
Epic → Estimation (with TDD dependencies) → Stories → Code Files
```

**Example:** "What would be affected if we change the users table?"
1. Find estimations with TDD components mentioning "users table"
2. Get all stories linked to those estimations
3. Get all code blocks linked to those stories
4. Identify dependent services from TDD dependencies in estimation

### Pattern 3: Progress Reporting

Aggregate across entities for status reports:

```
Epic → Estimation (with TDD) → Stories (grouped by status) → Code (change status)
```

**Example:** "What's the status of the Payment Gateway project?"
1. Get Epic details for context
2. Get estimation for effort summary and TDD technical scope
3. Aggregate stories by status
4. Count open vs merged changes
5. Calculate completion percentage

### Pattern 4: Historical Matching (AI Value Add)

Traverse history for recommendations:

**Step 1:** AI retrieves historical requirements based on new requirement
**Step 2:** AI recommends estimations (with TDD) based on historical data and identifies impacted modules
**Step 3:** AI creates respective Jira User Stories and Tasks
**Step 4:** AI recommends impacted files based on previous steps

---

## Vector Embedding Recommendations

### High-Priority Fields for Embedding

| File | Fields to Embed | Chunking Strategy |
|------|-----------------|-------------------|
| epics.csv | `epic_name + req_description` | Single chunk per epic |
| estimations.csv | `task_description + tdd_name + tdd_description + design_decisions` | Single chunk per estimation |
| stories_tasks.csv | `summary + description` | Single chunk per story |
| gitlab_code.json | `code_block_description + change_details` | Single chunk per code block |

### Metadata for Filtering

Always include these fields as metadata (not embedded):
- `epic_id`, `dev_est_id`, `tdd_id`, `jira_story_id`, `chg_id` - For joins
- `status`, `priority`, `complexity` - For filtering
- `created_at`, `updated_at` - For temporal queries
- `technical_components`, `labels` - For categorical filtering

---

## Data Statistics

| Metric | Count |
|--------|-------|
| Total Epics | 10 |
| Total Estimations (with TDD) | 10 |
| Total Stories/Tasks | 81 |
| Total Code Blocks | 81 |
| Unique Technologies | 25+ |
| Unique Teams | 6 |
| Programming Languages | 8 |

---

## End-to-End Traceability Example

```
EPIC/REQUIREMENTS: MM16783 (FOA Large Group Renewals) [POC ENTRY POINT]
│
│ • Epic_id: EPIC-001
│ • Epic_name: FOA Large Group Renewals Enhancement
│ • Req_description: GSF Excel Template Automation
│
└──► DEV/QA ESTIMATION: GB960 (Contains TDD as Technical Component)
    │
    │ • Dev_est_id: EST-001
    │ • Task_description: Build GSF Template Generator
    │ • Complexity: Large | Total Effort: 155 hrs
    │
    │ TDD (Technical Component):
    │ • TDD_id: TDD-001
    │ • TDD_name: GSF Template Technical Design
    │ • Technical_components: [Excel Gen, Kafka, DB]
    │ • Design_decisions: Use Kafka for async processing
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
• EPIC/Requirements ──► 1 Dev/QA Estimation with TDD (1:1)
• Dev/QA Estimation ──► 1 Jira Story/Task (1:1)
• Jira Story/Task ──► Multiple Gitlab Files (1:N)

Note: TDD is embedded as a technical component within the Estimation entity
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-02-28 | Initial synthetic data generation |
| 2.0 | 2025-12-26 | Updated hierarchy: EPIC → Estimation → TDD → Story → Code |
| 2.1 | 2025-12-26 | TDD embedded as technical component within Estimation |

---

## Contact

For questions about this data schema or AI agent integration, contact your project technical lead.
