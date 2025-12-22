# Enterprise Knowledge Base - Data Schema Documentation

## Overview

This document describes the synthetic data schema designed to enable AI agents to answer questions about software development projects by traversing relationships between Epics, Estimations, Technical Design Documents (TDDs), Stories/Tasks, and GitLab Code references.

The data follows a hierarchical structure that mirrors real-world enterprise software development workflows, enabling semantic search, relationship traversal, and contextual question answering.

---

## Data Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA RELATIONSHIP MODEL                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│    EPIC (1) ──────────────────┬──────────────────────────────────────   │
│      │                        │                                          │
│      │ 1:1                    │ 1:1                                      │
│      ▼                        ▼                                          │
│  ESTIMATION (1)            TDD (1) ─────────────┐                       │
│                               │                  │                       │
│                               │ 1:N              │                       │
│                               ▼                  │                       │
│                         TDD_SECTIONS (N)         │                       │
│                               │                  │                       │
│                               │ 1:N              │                       │
│                               ▼                  │                       │
│                        STORIES/TASKS (N) ◄───────┘                      │
│                               │                                          │
│                               │ 1:1                                      │
│                               ▼                                          │
│                        GITLAB_CODE (1)                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## File Descriptions

### 1. epics.csv

**Purpose:** Master reference for all major project initiatives

**Importance for AI Agents:**
- Serves as the **root entity** for all queries
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
| `epic_title` | String | Human-readable title | Semantic search, keyword matching |
| `epic_description` | String | Detailed description of the initiative | Semantic search, context retrieval |
| `epic_status` | Enum | Planning, In Progress, Done, Blocked | Filtering |
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
- "Who owns the authentication service project?"

---

### 2. estimations.csv

**Purpose:** Development and QA effort estimates linked to each Epic

**Importance for AI Agents:**
- Provides **resource planning context** for project decisions
- Enables capacity and workload analysis
- Links effort to complexity and risk assessments
- Essential for answering questions like:
  - "How many developer hours are allocated to the Payment Gateway?"
  - "Which projects have the highest risk level?"
  - "What's the total QA effort across all Commerce projects?"

**Schema:**

| Field | Type | Description | AI Search Relevance |
|-------|------|-------------|---------------------|
| `estimation_id` | String | Primary key (e.g., EST-001) | Exact match lookups |
| `epic_id` | String | Foreign key to epics.csv | Relationship traversal |
| `dev_hours` | Integer | Estimated development hours | Aggregation, comparison |
| `qa_hours` | Integer | Estimated QA/testing hours | Aggregation, comparison |
| `total_hours` | Integer | Combined effort hours | Aggregation |
| `total_story_points` | Integer | Agile story points sum | Velocity calculations |
| `complexity` | Enum | Low, Medium, High | Filtering, risk analysis |
| `risk_level` | Enum | Low, Medium, High | Filtering, prioritization |
| `estimation_method` | String | Planning Poker, T-Shirt, etc. | Context |
| `confidence_level` | Enum | Low, Medium, High | Reliability assessment |
| `estimated_by` | String | Person who created estimate | Accountability |
| `estimation_date` | Date | When estimate was made | Temporal context |
| `notes` | String | Additional context | Semantic search |

**Sample Queries Enabled:**
- "What's the total development effort for Q1 projects?"
- "Which high-complexity projects have low confidence estimates?"
- "Compare dev vs QA hours across all epics"

---

### 3. tdds.csv

**Purpose:** Technical Design Documents with section-level granularity

**Importance for AI Agents:**
- Contains **technical architecture details** for each project
- Section-level indexing enables precise answer retrieval
- Technology and dependency metadata enables impact analysis
- Essential for answering questions like:
  - "What technologies does the Order Management system use?"
  - "Which services depend on the auth-service?"
  - "What does the Data Model section say about the users table?"

**Schema:**

| Field | Type | Description | AI Search Relevance |
|-------|------|-------------|---------------------|
| `tdd_id` | String | TDD identifier (e.g., TDD-001) | Grouping sections |
| `epic_id` | String | Foreign key to epics.csv | Relationship traversal |
| `tdd_title` | String | Document title | Semantic search |
| `tdd_version` | String | Version number | Version filtering |
| `tdd_status` | Enum | Draft, In Review, Approved | Filtering |
| `tdd_author` | String | Document author email | Entity resolution |
| `tdd_created_date` | Date | Creation date | Temporal queries |
| `tdd_last_updated` | Date | Last modification | Freshness ranking |
| `tdd_technologies` | Array | Technologies used (comma-separated) | Technology search |
| `tdd_dependencies` | Array | Service dependencies (comma-separated) | Impact analysis |
| `tdd_section_id` | String | Unique section ID (e.g., TDD-001-SEC-03) | Precise retrieval |
| `tdd_section_name` | String | Section heading | Semantic search |
| `tdd_section_order` | Integer | Section sequence number | Ordering |
| `tdd_section_content_summary` | String | Section summary/content | Semantic search, RAG |

**Sample Queries Enabled:**
- "What's the security architecture for the payment gateway?"
- "Which projects use Kafka?"
- "Show me all API endpoint documentation"
- "What are the dependencies for the notification service?"

---

### 4. stories_tasks.csv

**Purpose:** Jira-style work items linked to TDD sections

**Importance for AI Agents:**
- Provides **granular work breakdown** for each project
- Links implementation tasks to specific TDD sections
- Enables progress tracking and sprint analysis
- Essential for answering questions like:
  - "What stories are assigned to Sprint-25?"
  - "Which tasks implement the Security section of the auth TDD?"
  - "What's the status of all payment-related stories?"

**Schema:**

| Field | Type | Description | AI Search Relevance |
|-------|------|-------------|---------------------|
| `story_id` | String | Primary key (e.g., AUTH-101) | Exact match lookups |
| `epic_id` | String | Foreign key to epics.csv | Hierarchy traversal |
| `tdd_id` | String | Foreign key to TDD | Document linkage |
| `tdd_section_id` | String | Foreign key to TDD section | Precise context |
| `story_title` | String | Task/story title | Semantic search |
| `story_type` | Enum | Feature, Task, Bug, Spike | Filtering |
| `story_status` | Enum | To Do, In Progress, Done | Progress tracking |
| `story_points` | Integer | Effort estimate | Velocity, aggregation |
| `story_assignee` | String | Assigned developer email | Workload analysis |
| `story_sprint` | String | Sprint identifier | Sprint filtering |
| `acceptance_criteria` | String | Definition of done | Semantic search |
| `story_created_date` | Date | Creation date | Temporal queries |
| `story_updated_date` | Date | Last update | Change tracking |
| `parent_story_id` | String | Parent story (for subtasks) | Hierarchy |
| `labels` | Array | Tags (comma-separated) | Categorical filtering |

**Sample Queries Enabled:**
- "What features are in Sprint-26?"
- "Show me all blocked tasks for the mobile backend"
- "Which developer has the most story points assigned?"
- "List all security-labeled tasks across projects"

---

### 5. gitlab_code.json

**Purpose:** GitLab code references linked to stories and TDD sections

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
| `code_id` | String | Primary key (e.g., CODE-001) | Exact match |
| `story_id` | String | Foreign key to stories_tasks.csv | Work item linkage |
| `epic_id` | String | Foreign key to epics.csv | Project context |
| `tdd_section_id` | String | Foreign key to TDD section | Design traceability |
| `gitlab_repo` | String | Repository path | Repository filtering |
| `gitlab_branch` | String | Feature branch name | Branch tracking |
| `gitlab_file_path` | String | File path in repository | File-level queries |
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
| `sonar_issues` | Integer | Static analysis issues | Quality metrics |

**Sample Queries Enabled:**
- "What code implements the password reset feature?"
- "Show me all Python files in the payment service"
- "Which merge requests are still open?"
- "What's the average code coverage across all services?"

---

## Relationship Mapping Reference

### Primary Key → Foreign Key Relationships

```
epics.csv
└── epic_id (PK)
    ├── estimations.csv.epic_id (FK) [1:1]
    ├── tdds.csv.epic_id (FK) [1:N via sections]
    ├── stories_tasks.csv.epic_id (FK) [1:N]
    └── gitlab_code.json.epic_id (FK) [1:N]

tdds.csv
├── tdd_id (PK-partial)
│   └── stories_tasks.csv.tdd_id (FK)
└── tdd_section_id (PK)
    ├── stories_tasks.csv.tdd_section_id (FK)
    └── gitlab_code.json.tdd_section_id (FK)

stories_tasks.csv
└── story_id (PK)
    └── gitlab_code.json.story_id (FK) [1:1]
```

### Cross-Reference Query Examples

| Query Type | Files Involved | Join Path |
|------------|---------------|-----------|
| "Get all code for an Epic" | epics → gitlab_code | epic_id |
| "Get TDD section for code" | gitlab_code → tdds | tdd_section_id |
| "Get estimation for a story" | stories → epics → estimations | epic_id |
| "Get all stories for a TDD section" | tdds → stories | tdd_section_id |

---

## AI Agent Usage Patterns

### Pattern 1: Hierarchical Context Retrieval

When a user asks about code, retrieve the full context chain:

```
Code Block → Story → TDD Section → TDD → Epic → Estimation
```

**Example:** "Explain the JWT implementation"
1. Search `gitlab_code.json` for JWT-related code
2. Get linked `story_id` → retrieve story context
3. Get linked `tdd_section_id` → retrieve design rationale
4. Get linked `epic_id` → retrieve project goals
5. Synthesize comprehensive answer

### Pattern 2: Impact Analysis

When analyzing changes, traverse dependencies:

```
Epic → TDD (dependencies) → Related Epics → Related Stories
```

**Example:** "What would be affected if we change the users table?"
1. Find TDD sections mentioning "users table"
2. Get all stories linked to those sections
3. Get all code blocks linked to those stories
4. Identify dependent services from TDD dependencies

### Pattern 3: Progress Reporting

Aggregate across entities for status reports:

```
Epic → Stories (grouped by status) → Code (MR status)
```

**Example:** "What's the status of the Payment Gateway project?"
1. Get Epic details for context
2. Aggregate stories by status
3. Count open vs merged MRs
4. Calculate completion percentage

---

## Vector Embedding Recommendations

### High-Priority Fields for Embedding

| File | Fields to Embed | Chunking Strategy |
|------|-----------------|-------------------|
| epics.csv | `epic_title + epic_description` | Single chunk per epic |
| tdds.csv | `tdd_section_name + tdd_section_content_summary` | One chunk per section |
| stories_tasks.csv | `story_title + acceptance_criteria` | Single chunk per story |
| gitlab_code.json | `code_block_description + functions_defined` | Single chunk per code block |

### Metadata for Filtering

Always include these fields as metadata (not embedded):
- `epic_id`, `tdd_id`, `story_id`, `code_id` - For joins
- `status`, `priority`, `team` - For filtering
- `created_at`, `updated_at` - For temporal queries
- `technologies`, `labels` - For categorical filtering

---

## Data Statistics

| Metric | Count |
|--------|-------|
| Total Epics | 10 |
| Total Estimations | 10 |
| Total TDD Documents | 10 |
| Total TDD Sections | 51 |
| Total Stories/Tasks | 81 |
| Total Code Blocks | 81 |
| Unique Technologies | 25+ |
| Unique Teams | 6 |
| Programming Languages | 8 |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-02-28 | Initial synthetic data generation |

---

## Contact

For questions about this data schema or AI agent integration, contact your project technical lead.
