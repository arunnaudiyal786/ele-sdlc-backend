# SDLC Agent Outputs Implementation Plan

## Executive Summary

**FINDING: All five requested capabilities are already implemented** in the ele-sdlc-backend system. The codebase has a complete LangGraph multi-agent pipeline that processes a requirement input and produces all requested outputs.

---

## Requested Capabilities vs. Current Implementation

| # | Requirement | Status | Current Implementation |
|---|-------------|--------|------------------------|
| 1a | Extract historical requirements | ✅ **IMPLEMENTED** | `search` agent + hybrid vector search |
| 1b | Create estimation sheet | ✅ **IMPLEMENTED** | `effort` agent with dev/QA hours, story points |
| 1c | Create TDD document | ⚠️ **PARTIAL** | TDD data indexed in search, but no dedicated TDD generation agent |
| 1d | Technical modules impacted | ✅ **IMPLEMENTED** | `modules` agent outputs functional + technical modules |
| 1e | Jira stories | ✅ **IMPLEMENTED** | `stories` agent generates full Jira stories |

---

## Detailed Analysis

### 1a. Historical Requirements Extraction ✅

**Location:** `app/components/search/`

**What exists:**
- `HybridSearchService` performs semantic + keyword search
- Searches across `epics`, `estimations`, `tdds` ChromaDB collections
- Returns scored matches with metadata (hours, technologies, team)

**Workflow step:** `search_agent` → `auto_select_node` (top 5 matches)

**Output includes:**
```python
{
    "epic_id": "EPIC-001",
    "epic_name": "Payment Gateway Integration",
    "score": 0.85,
    "estimated_hours": 165,
    "actual_hours": 180,
    "technologies": ["Python", "FastAPI", "PostgreSQL"]
}
```

---

### 1b. Estimation Sheet ✅

**Location:** `app/components/effort/`

**What exists:**
- `EffortService` generates effort estimates via LLM
- Uses historical matches + identified modules for context
- Outputs breakdown by module

**Output matches your estimations.csv structure:**

| estimations.csv Column | Current Output Field | Notes |
|------------------------|---------------------|-------|
| `dev_effort_hours` | `total_dev_hours` | ✅ Present |
| `qa_effort_hours` | `total_qa_hours` | ✅ Present |
| `total_effort_hours` | `total_hours` | ✅ Present |
| `total_story_points` | `story_points` | ✅ Present |
| `confidence_level` | `confidence` | ✅ Present (LOW/MEDIUM/HIGH) |
| `complexity` | ❌ | **Missing** - can be added |
| `risk_level` | ❌ | Handled by separate `risks` agent |
| `estimation_method` | ❌ | **Missing** - can be added |
| `other_params` | ❌ | **Missing** - can be added |

---

### 1c. TDD Document Generation ⚠️ PARTIAL

**Current state:**
- TDD data is **indexed and searchable** via ChromaDB
- Historical TDDs are returned in search results
- **No dedicated TDD generation agent exists**

**tdds.csv structure vs. current capabilities:**

| tdds.csv Column | Current Support | Notes |
|-----------------|-----------------|-------|
| `tdd_name` | ❌ | Not generated |
| `tdd_description` | ❌ | Not generated |
| `technical_components` | ⚠️ Partial | `modules` agent outputs technical modules |
| `design_decisions` | ❌ | Not generated |
| `architecture_pattern` | ❌ | Not generated |
| `security_considerations` | ⚠️ | `risks` agent captures some |
| `performance_requirements` | ❌ | Not generated |
| `tdd_dependencies` | ❌ | Not generated |

**Recommendation:** Create a new `tdd` agent to generate TDD documents.

---

### 1d. Technical Modules Impacted ✅

**Location:** `app/components/modules/`

**What exists:**
- `ModulesService` identifies functional and technical modules
- LLM-based analysis with impact levels (HIGH/MEDIUM/LOW)
- Outputs 5-6 functional + 4-5 technical modules

**Output example:**
```python
{
    "functional_modules": [
        {"name": "Payment Processing", "impact": "HIGH", "description": "..."},
        {"name": "Transaction Logging", "impact": "MEDIUM", "description": "..."}
    ],
    "technical_modules": [
        {"name": "API Gateway", "impact": "HIGH", "description": "..."},
        {"name": "Database Layer", "impact": "MEDIUM", "description": "..."}
    ]
}
```

---

### 1e. Jira Stories ✅

**Location:** `app/components/stories/`

**What exists:**
- `StoriesService` generates Jira-style stories
- Includes story type, points, acceptance criteria, priority
- Based on modules and effort outputs

**Output matches stories_tasks.csv structure:**

| stories_tasks.csv Column | Current Output Field | Notes |
|--------------------------|---------------------|-------|
| `summary` | `title` | ✅ Present |
| `description` | `description` | ✅ Present |
| `issue_type` | `story_type` | ✅ Present (Story/Task/Bug/Spike) |
| `story_points` | `story_points` | ✅ Present |
| `priority` | `priority` | ✅ Present |
| `acceptance_criteria` | `acceptance_criteria` | ✅ Present (list) |
| `labels` | ❌ | **Missing** - can be added |
| `assignee` | ❌ | Not applicable (generation) |
| `sprint` | ❌ | Not applicable (generation) |

---

## Implementation Plan

### Option A: Confirm Everything Works (Recommended First)

Since most functionality exists, verify the pipeline produces all outputs:

```bash
# 1. Activate virtual environment
source /Users/arunnaudiyal/Elevance\ Health/SDLC/Code/ele-sdlc-backend/.venv/bin/activate

# 2. Start the API server
python api_server.py

# 3. Test the pipeline with a sample requirement
curl -X POST http://localhost:8000/api/v1/impact/run-pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-001",
    "requirement_text": "Build a user authentication service with OAuth 2.0, MFA support, and SSO integration for enterprise clients"
  }'
```

Expected outputs in response:
- `modules_output` → Technical modules impacted (1d)
- `effort_output` → Estimation sheet (1b)
- `stories_output` → Jira stories (1e)
- Historical extraction happens via `selected_matches` in state (1a)

---

### Option B: Create TDD Generation Agent (If Needed)

**Files to create:**

```
app/components/tdd/
├── __init__.py
├── agent.py          # LangGraph node function
├── models.py         # TDDRequest, TDDResponse, TDDItem
├── prompts.py        # System and user prompts
├── service.py        # TDDService class
└── README.md
```

**Workflow modification:**

```python
# In app/components/orchestrator/workflow.py
# Add after effort agent, before stories:

workflow.add_node("tdd", tdd_agent)
workflow.add_edge("effort", "tdd")
workflow.add_edge("tdd", "stories")
```

**TDD Output Model (based on tdds.csv):**

```python
class TDDItem(BaseModel):
    tdd_name: str
    tdd_description: str
    technical_components: List[str]
    design_decisions: str
    architecture_pattern: str
    security_considerations: str
    performance_requirements: str
    tdd_dependencies: List[str]

class TDDResponse(BaseModel):
    session_id: str
    tdd: TDDItem
    generated_at: datetime
```

---

### Option C: Enhance Existing Agents

If you want outputs to match CSV columns exactly:

| Enhancement | File | Change |
|-------------|------|--------|
| Add `complexity` to effort | `app/components/effort/models.py` | Add field to `EffortResponse` |
| Add `estimation_method` | `app/components/effort/prompts.py` | Update prompt to include |
| Add `labels` to stories | `app/components/stories/models.py` | Add field to `StoryItem` |
| Add `risk_level` to effort | `app/components/effort/service.py` | Cross-reference with risks output |

---

## Current Workflow Diagram

```
┌─────────────────┐
│   Requirement   │ ← Input: requirement_text
│     Agent       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Search Agent  │ ← OUTPUT 1a: Historical requirements extracted
│ (Hybrid Search) │   Returns: all_matches with scores
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Auto-Select    │ ← Selects top 5 matches
│     Node        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Modules Agent  │ ← OUTPUT 1d: Technical modules impacted
│                 │   Returns: functional_modules, technical_modules
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Effort Agent   │ ← OUTPUT 1b: Estimation sheet
│                 │   Returns: dev_hours, qa_hours, story_points
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Stories Agent  │ ← OUTPUT 1e: Jira stories
│                 │   Returns: stories with AC, points, priority
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Code Impact     │
│    Agent        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Risks Agent    │
└────────┬────────┘
         │
         ▼
      [END]
```

**Missing in workflow:** TDD Generation Agent (1c)

---

## Recommended Next Steps

1. **Verify existing pipeline** - Run the API and confirm outputs for 1a, 1b, 1d, 1e

2. **Create TDD Agent** (if TDD generation is required) - Follow Option B structure

3. **Enhance output formats** (if exact CSV column match needed) - Follow Option C

---

## File Locations Reference

### Existing Agents
- `app/components/search/service.py:1` - Historical extraction
- `app/components/modules/service.py:1` - Technical modules
- `app/components/effort/service.py:1` - Estimation
- `app/components/stories/service.py:1` - Jira stories

### Data Files
- `data/raw/estimations.csv` - Estimation column structure
- `data/raw/tdds.csv` - TDD column structure
- `data/raw/stories_tasks.csv` - Stories column structure

### Orchestration
- `app/components/orchestrator/workflow.py:98` - `create_impact_workflow()`

---

## Questions for Clarification

1. **TDD Generation**: Do you need the system to **generate new TDD documents** from requirements, or is it sufficient that historical TDDs are returned via search?

2. **Output Format**: Do you need the outputs in the exact CSV column format, or is the current JSON response structure acceptable?

3. **Export Functionality**: Do you need to export results to CSV/Excel files, or is JSON API response sufficient?

---

## Conclusion

**4 out of 5 capabilities are fully implemented.** The only gap is a dedicated TDD generation agent (1c). The system can:

- ✅ Extract historical requirements via hybrid search
- ✅ Generate estimation sheets with hours and story points
- ⚠️ Generate TDD documents (needs new agent)
- ✅ Identify technical modules with impact levels
- ✅ Generate Jira stories with acceptance criteria

If TDD generation is critical, creating the `app/components/tdd/` agent following the existing component pattern would take approximately 5-6 files matching the architecture of other agents.
