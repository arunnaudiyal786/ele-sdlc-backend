# How-To Guide

Practical recipes for common development tasks in the AI Impact Assessment System.

## Table of Contents

- [Add a New Component](#add-a-new-component)
- [Add Agent to Workflow](#add-agent-to-workflow)
- [Add ChromaDB Collection](#add-chromadb-collection)
- [Modify LLM Prompts](#modify-llm-prompts)
- [Add New Endpoint](#add-new-endpoint)
- [Testing Your Changes](#testing-your-changes)
- [Update Data Schema](#update-data-schema)
- [Add Configuration Options](#add-configuration-options)

---

## Add a New Component

**Goal:** Create a new feature component following the standard pattern.

**Example:** Create a "risk_assessment" component that analyzes project risks.

### Step 1: Create Component Directory

```bash
mkdir -p app/components/risk_assessment
cd app/components/risk_assessment
touch __init__.py models.py service.py agent.py router.py prompts.py
```

### Step 2: Define Models (`models.py`)

```python
"""Risk Assessment data models."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class RiskAssessmentRequest(BaseModel):
    """Request to assess project risks."""
    session_id: str
    requirement_text: str
    selected_matches: List[dict] = []
    impacted_modules: List[dict] = []


class Risk(BaseModel):
    """Individual risk item."""
    category: str = Field(..., description="technical, resource, schedule, or external")
    description: str = Field(..., min_length=10)
    probability: str = Field(..., pattern="^(high|medium|low)$")
    impact: str = Field(..., pattern="^(high|medium|low)$")
    mitigation: str = Field(..., min_length=10)


class RiskAssessmentResponse(BaseModel):
    """Risk assessment results."""
    session_id: str
    risks: List[Risk]
    overall_risk_level: str = Field(..., pattern="^(high|medium|low)$")
    created_at: datetime = Field(default_factory=datetime.now)
```

### Step 3: Create Service (`service.py`)

```python
"""Risk Assessment service."""
import json
from typing import Dict, Any
from app.components.base import BaseComponent, get_settings
from app.components.base.exceptions import ResponseParsingError
from app.utils.audit import AuditTrailManager
from app.utils.json_repair import parse_llm_json
from .models import RiskAssessmentRequest, RiskAssessmentResponse, Risk
from .prompts import RISK_ASSESSMENT_PROMPT
import requests


class RiskAssessmentService(BaseComponent[RiskAssessmentRequest, RiskAssessmentResponse]):
    """Assess project risks using LLM."""

    def __init__(self):
        self.config = get_settings()
        self.ollama_url = f"{self.config.ollama_base_url}/api/generate"

    @property
    def component_name(self) -> str:
        return "risk_assessment"

    async def process(self, request: RiskAssessmentRequest) -> RiskAssessmentResponse:
        """Generate risk assessment."""
        # 1. Build prompt
        prompt = self._build_prompt(request)

        # 2. Call LLM
        raw_response = await self._call_llm(prompt)

        # 3. Parse response
        parsed_risks = self._parse_response(raw_response)

        # 4. Save to audit trail
        audit = AuditTrailManager(request.session_id)
        audit.save_text(
            "input_prompt.txt",
            prompt,
            subfolder="step3_agents/agent_risk_assessment",
        )
        audit.save_text(
            "raw_response.txt",
            raw_response,
            subfolder="step3_agents/agent_risk_assessment",
        )
        audit.save_json(
            "parsed_output.json",
            parsed_risks,
            subfolder="step3_agents/agent_risk_assessment",
        )

        # 5. Calculate overall risk
        overall_risk = self._calculate_overall_risk(parsed_risks)

        return RiskAssessmentResponse(
            session_id=request.session_id,
            risks=[Risk(**r) for r in parsed_risks],
            overall_risk_level=overall_risk,
        )

    def _build_prompt(self, request: RiskAssessmentRequest) -> str:
        """Build LLM prompt."""
        return RISK_ASSESSMENT_PROMPT.format(
            requirement=request.requirement_text,
            matches=json.dumps(request.selected_matches, indent=2),
            modules=json.dumps(request.impacted_modules, indent=2),
        )

    async def _call_llm(self, prompt: str) -> str:
        """Call Ollama LLM."""
        payload = {
            "model": self.config.ollama_gen_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.ollama_temperature,
            },
        }

        response = requests.post(
            self.ollama_url,
            json=payload,
            timeout=self.config.ollama_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()["response"]

    def _parse_response(self, raw: str) -> List[Dict[str, Any]]:
        """Parse LLM JSON response."""
        try:
            data = parse_llm_json(raw)
            return data.get("risks", [])
        except Exception as e:
            raise ResponseParsingError(
                message=f"Failed to parse risk assessment: {e}",
                component=self.component_name,
                details={"raw_response": raw[:500]},
            )

    def _calculate_overall_risk(self, risks: List[Dict]) -> str:
        """Calculate overall risk level."""
        high_count = sum(1 for r in risks if r.get("impact") == "high")
        if high_count >= 2:
            return "high"
        elif high_count == 1 or any(r.get("probability") == "high" for r in risks):
            return "medium"
        return "low"
```

### Step 4: Create Prompts (`prompts.py`)

```python
"""Risk Assessment LLM prompts."""

RISK_ASSESSMENT_PROMPT = """You are a software project risk assessor. Analyze the requirement and identify potential risks.

**Requirement:**
{requirement}

**Historical Similar Projects:**
{matches}

**Impacted Modules:**
{modules}

**Task:**
Identify 3-5 key risks for this project. For each risk, provide:
- category: one of [technical, resource, schedule, external]
- description: clear explanation of the risk
- probability: high, medium, or low
- impact: high, medium, or low (if risk occurs)
- mitigation: how to reduce or manage this risk

Return ONLY valid JSON in this EXACT format:
{{
  "risks": [
    {{
      "category": "technical",
      "description": "Legacy system integration complexity",
      "probability": "high",
      "impact": "medium",
      "mitigation": "Allocate 2 weeks for integration testing"
    }}
  ]
}}

Return ONLY the JSON, no extra text.
"""
```

### Step 5: Create Agent (`agent.py`)

```python
"""Risk Assessment LangGraph agent."""
from typing import Dict, Any
from .service import RiskAssessmentService
from .models import RiskAssessmentRequest


_service: RiskAssessmentService | None = None


def get_service() -> RiskAssessmentService:
    """Singleton service factory."""
    global _service
    if _service is None:
        _service = RiskAssessmentService()
    return _service


async def risk_assessment_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for risk assessment.

    Returns PARTIAL state update.
    """
    try:
        service = get_service()

        request = RiskAssessmentRequest(
            session_id=state["session_id"],
            requirement_text=state["requirement_text"],
            selected_matches=state.get("selected_matches", []),
            impacted_modules=state.get("impacted_modules_output", {}).get("modules", []),
        )

        response = await service.process(request)

        return {
            "risks_output": response.model_dump(),
            "status": "risks_generated",
            "current_agent": "END",  # Last agent in pipeline
            "messages": [
                {
                    "role": "risk_assessment",
                    "content": f"Identified {len(response.risks)} risks",
                }
            ],
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler",
        }
```

### Step 6: Create Router (`router.py`)

```python
"""Risk Assessment REST API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from app.components.base.exceptions import ComponentError
from .agent import get_service
from .models import RiskAssessmentRequest, RiskAssessmentResponse
from .service import RiskAssessmentService


router = APIRouter(prefix="/risk-assessment", tags=["Risk Assessment"])


@router.post("/assess", response_model=RiskAssessmentResponse)
async def assess_risks(
    request: RiskAssessmentRequest,
    service: RiskAssessmentService = Depends(get_service),
) -> RiskAssessmentResponse:
    """Assess project risks."""
    try:
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())


@router.get("/health")
async def health_check(
    service: RiskAssessmentService = Depends(get_service),
):
    """Component health check."""
    return await service.health_check()
```

### Step 7: Update `__init__.py`

```python
"""Risk Assessment component public exports."""
from .models import RiskAssessmentRequest, RiskAssessmentResponse, Risk
from .service import RiskAssessmentService
from .agent import risk_assessment_agent, get_service
from .router import router


__all__ = [
    "RiskAssessmentRequest",
    "RiskAssessmentResponse",
    "Risk",
    "RiskAssessmentService",
    "risk_assessment_agent",
    "get_service",
    "router",
]
```

### Step 8: Register Router in Main App

Edit `app/main.py`:

```python
from app.components.risk_assessment import router as risk_router

# ... existing imports ...

app = FastAPI(title="AI Impact Assessment System")

# ... existing routers ...

# Add new router
app.include_router(risk_router, prefix="/api/v1")
```

### Step 9: Test the Component

```bash
# 1. Start server
./start_dev.sh

# 2. Test endpoint
curl -X POST http://localhost:8000/api/v1/risk-assessment/assess \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session",
    "requirement_text": "Build user authentication system",
    "selected_matches": [],
    "impacted_modules": []
  }'

# 3. Check health
curl http://localhost:8000/api/v1/risk-assessment/health
```

### Step 10: Add Tests

Create `tests/test_risk_assessment.py`:

```python
"""Tests for Risk Assessment component."""
import pytest
from app.components.risk_assessment import RiskAssessmentService, RiskAssessmentRequest


@pytest.mark.asyncio
async def test_risk_assessment_process():
    """Test risk assessment processing."""
    service = RiskAssessmentService()
    request = RiskAssessmentRequest(
        session_id="test_session",
        requirement_text="Build complex integration system",
        selected_matches=[],
        impacted_modules=[],
    )

    response = await service.process(request)

    assert response.session_id == "test_session"
    assert len(response.risks) > 0
    assert response.overall_risk_level in ["high", "medium", "low"]


def test_overall_risk_calculation():
    """Test overall risk level calculation."""
    service = RiskAssessmentService()

    # High risks -> overall high
    risks = [
        {"impact": "high", "probability": "high"},
        {"impact": "high", "probability": "medium"},
    ]
    assert service._calculate_overall_risk(risks) == "high"

    # Low risks -> overall low
    risks = [
        {"impact": "low", "probability": "low"},
        {"impact": "low", "probability": "low"},
    ]
    assert service._calculate_overall_risk(risks) == "low"
```

Run tests:
```bash
pytest tests/test_risk_assessment.py -v
```

---

## Add Agent to Workflow

**Goal:** Integrate the new component into the LangGraph workflow.

### Step 1: Update State Definition

Edit `app/components/orchestrator/state.py`:

```python
from typing import TypedDict, List, Dict, Any, Annotated
import operator


class State(TypedDict):
    """LangGraph workflow state."""
    # ... existing fields ...

    # Add new field for risk assessment output
    risks_output: Dict[str, Any]  # ← Add this
```

### Step 2: Add Node to Workflow

Edit `app/components/orchestrator/workflow.py`:

```python
from langgraph.graph import StateGraph, END
from .state import State

# Import new agent
from app.components.risk_assessment import risk_assessment_agent

# ... existing imports ...

# Create workflow
workflow = StateGraph(State)

# ... existing nodes ...

# Add new node
workflow.add_node("risk_assessment", risk_assessment_agent)
```

### Step 3: Add Edges

```python
# Connect to workflow
# Option A: Sequential (after jira_stories)
workflow.add_edge("jira_stories", "risk_assessment")
workflow.add_edge("risk_assessment", END)

# Option B: Conditional (based on state)
def should_assess_risks(state: Dict[str, Any]) -> str:
    """Decide if risk assessment needed."""
    if state.get("high_complexity", False):
        return "risk_assessment"
    return END

workflow.add_conditional_edges(
    "jira_stories",
    should_assess_risks,
    {
        "risk_assessment": "risk_assessment",
        END: END,
    }
)
workflow.add_edge("risk_assessment", END)
```

### Step 4: Update Status Enum

Edit `app/components/orchestrator/state.py`:

```python
from enum import Enum


class PipelineStatus(str, Enum):
    """Valid pipeline status values."""
    CREATED = "created"
    REQUIREMENT_SUBMITTED = "requirement_submitted"
    MATCHES_FOUND = "matches_found"
    # ... existing statuses ...
    JIRA_STORIES_GENERATED = "jira_stories_generated"
    RISKS_GENERATED = "risks_generated"  # ← Add this
    COMPLETED = "completed"
    ERROR = "error"
```

### Step 5: Test Workflow Integration

```python
# test_workflow.py
import asyncio
from app.components.orchestrator.workflow import workflow


async def test_full_pipeline():
    """Test complete workflow with new agent."""
    initial_state = {
        "session_id": "test_123",
        "requirement_text": "Build user authentication system",
        "status": "created",
    }

    # Run workflow
    result = await workflow.ainvoke(initial_state)

    # Verify risk assessment ran
    assert "risks_output" in result
    assert result["status"] == "risks_generated" or result["status"] == "completed"
    print(f"✅ Workflow completed with {len(result.get('risks_output', {}).get('risks', []))} risks")


asyncio.run(test_full_pipeline())
```

---

## Add ChromaDB Collection

**Goal:** Add a new collection to store and search additional data.

### Step 1: Define Data Schema

Create `data/raw/code_samples.csv`:

```csv
code_id,module_name,function_name,language,code_snippet,description,tags
CODE-001,auth,validate_user,python,"def validate_user(...)","User validation logic","auth,validation"
CODE-002,api,rate_limiter,python,"@decorator\ndef rate_limit(...)","Rate limiting decorator","api,security"
```

### Step 2: Update Vector Store Manager

Edit `app/rag/vector_store.py`:

```python
class VectorStoreManager:
    """ChromaDB vector store manager."""

    COLLECTIONS = {
        "epics": "Historical project epics",
        "estimations": "Effort estimation data",
        "tdds": "Technical Design Documents",
        "code_samples": "Reusable code examples",  # ← Add this
    }

    def get_or_create_collection(self, name: str):
        """Get or create a collection."""
        if name not in self.COLLECTIONS:
            raise ValueError(f"Invalid collection: {name}")

        return self.client.get_or_create_collection(
            name=f"{self.config.chroma_collection_prefix}_{name}",
            metadata={"description": self.COLLECTIONS[name]},
        )
```

### Step 3: Create Indexing Script

Create `scripts/index_code_samples.py`:

```python
"""Index code samples into ChromaDB."""
import pandas as pd
from app.rag.vector_store import VectorStoreManager
from app.rag.embeddings import OllamaEmbeddingService


def index_code_samples():
    """Index code samples CSV into ChromaDB."""
    print("Loading code samples...")
    df = pd.read_csv("data/raw/code_samples.csv")

    print(f"Found {len(df)} code samples")

    # Initialize services
    store = VectorStoreManager.get_instance()
    embedding_service = OllamaEmbeddingService.get_instance()

    # Get or create collection
    collection = store.get_or_create_collection("code_samples")

    # Prepare documents
    documents = []
    metadatas = []
    ids = []

    for _, row in df.iterrows():
        # Create searchable text
        text = f"{row['function_name']} - {row['description']}\n{row['code_snippet']}"
        documents.append(text)

        # Store metadata
        metadatas.append({
            "code_id": row["code_id"],
            "module_name": row["module_name"],
            "function_name": row["function_name"],
            "language": row["language"],
            "tags": row["tags"],
        })

        ids.append(row["code_id"])

    # Generate embeddings
    print("Generating embeddings...")
    embeddings = [embedding_service.embed_query(doc) for doc in documents]

    # Add to collection
    print("Adding to ChromaDB...")
    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )

    print(f"✅ Indexed {len(documents)} code samples")


if __name__ == "__main__":
    index_code_samples()
```

Run indexing:
```bash
python scripts/index_code_samples.py
```

### Step 4: Add Search Function

Edit `app/rag/hybrid_search.py`:

```python
async def search_code_samples(
    self,
    query: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Search code samples collection."""
    return await self.search(
        query=query,
        collections=["code_samples"],
        top_k=top_k,
    )
```

### Step 5: Test Collection

```bash
python -c "
from app.rag.vector_store import VectorStoreManager
from app.rag.hybrid_search import HybridSearchService

store = VectorStoreManager.get_instance()
search = HybridSearchService.get_instance()

# Verify collection
collection = store.get_collection('code_samples')
print(f'Code samples count: {collection.count()}')

# Test search
results = search.search_code_samples('authentication validation')
print(f'Found {len(results)} matches')
for r in results[:3]:
    print(f'  - {r[\"metadata\"][\"function_name\"]}: {r[\"final_score\"]:.2f}')
"
```

---

## Modify LLM Prompts

**Goal:** Improve prompt quality for better LLM responses.

### Best Practices

1. **Be specific** - Clear instructions > vague requests
2. **Provide examples** - Show exact format desired
3. **Constrain output** - Request specific structure/schema
4. **Add validation** - Request "return ONLY JSON, no extra text"
5. **Use context** - Include relevant historical data

### Example: Improving TDD Prompt

Edit `app/components/tdd/prompts.py`:

**❌ Before (Weak Prompt):**
```python
WEAK_PROMPT = """
Generate a Technical Design Document for this requirement:
{requirement}

Include sections for overview, architecture, and implementation.
"""
```

**✅ After (Strong Prompt):**
```python
TDD_GENERATION_PROMPT = """You are a senior software architect. Create a detailed Technical Design Document.

**Requirement:**
{requirement}

**Historical Similar Projects:**
{historical_context}

**Estimated Effort:** {estimated_hours} hours

**Task:**
Generate a comprehensive TDD with these EXACT sections:

1. **Overview** (2-3 sentences)
2. **Architecture** (list 3-5 key components)
3. **Implementation Plan** (list 5-8 steps)
4. **Technical Stack** (list technologies)
5. **Database Changes** (describe schema changes)
6. **API Endpoints** (list new endpoints)
7. **Testing Strategy** (unit, integration, e2e)
8. **Deployment Steps** (list steps)

Return response in this EXACT JSON format:
{{
  "overview": "Brief 2-3 sentence summary...",
  "architecture": [
    {{"component": "API Gateway", "purpose": "Request routing", "technology": "FastAPI"}}
  ],
  "implementation_plan": [
    {{"step": 1, "description": "Set up project structure", "duration_hours": 4}}
  ],
  "technical_stack": ["Python 3.10", "FastAPI", "PostgreSQL"],
  "database_changes": "Add users table with columns...",
  "api_endpoints": [
    {{"method": "POST", "path": "/auth/login", "description": "User login"}}
  ],
  "testing_strategy": {{"unit": "...", "integration": "...", "e2e": "..."}},
  "deployment_steps": ["Build Docker image", "Deploy to staging", ...]
}}

IMPORTANT:
- Return ONLY the JSON object, no markdown code blocks
- No extra explanatory text before or after JSON
- All strings must be properly escaped
- Include realistic technical details from similar projects
"""
```

### Testing Prompt Changes

```python
# test_prompts.py
from app.components.tdd.service import TDDService


async def test_prompt_quality():
    """Test prompt generates expected output."""
    service = TDDService()

    request = TDDRequest(
        session_id="test",
        requirement_text="Build user authentication with OAuth2",
        historical_context=[...],
        estimated_hours=120,
    )

    response = await service.process(request)

    # Verify all expected sections present
    assert "overview" in response.tdd_content
    assert len(response.architecture_components) >= 3
    assert len(response.implementation_steps) >= 5
    assert len(response.technical_stack) > 0

    print("✅ Prompt generates well-structured output")
```

---

## Add New Endpoint

**Goal:** Add a standalone API endpoint (not part of workflow).

### Example: Endpoint to List Recent Sessions

Edit appropriate router (or create new):

```python
# app/components/session/router.py
from fastapi import APIRouter, Query
from typing import List, Optional
from datetime import datetime, timedelta
import os
import json


router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("/recent", response_model=List[Dict[str, Any]])
async def list_recent_sessions(
    days: int = Query(default=7, ge=1, le=30),
    status: Optional[str] = Query(default=None),
) -> List[Dict[str, Any]]:
    """List recent sessions from audit trail.

    Args:
        days: Number of days to look back (1-30)
        status: Filter by status (optional)

    Returns:
        List of session summaries
    """
    sessions = []
    cutoff_date = datetime.now() - timedelta(days=days)

    # Scan sessions directory
    sessions_dir = "sessions"
    if not os.path.exists(sessions_dir):
        return []

    # Iterate through date directories
    for date_dir in os.listdir(sessions_dir):
        date_path = os.path.join(sessions_dir, date_dir)
        if not os.path.isdir(date_path):
            continue

        # Parse date
        try:
            dir_date = datetime.strptime(date_dir, "%Y-%m-%d")
        except ValueError:
            continue

        if dir_date < cutoff_date:
            continue

        # Check each session in this date
        for session_id in os.listdir(date_path):
            session_path = os.path.join(date_path, session_id)

            # Load final summary
            summary_file = os.path.join(session_path, "final_summary.json")
            if os.path.exists(summary_file):
                with open(summary_file) as f:
                    summary = json.load(f)

                    # Apply status filter
                    if status and summary.get("status") != status:
                        continue

                    sessions.append({
                        "session_id": session_id,
                        "date": date_dir,
                        "status": summary.get("status"),
                        "requirement": summary.get("requirement_text", "")[:100],
                        "created_at": summary.get("created_at"),
                    })

    # Sort by date descending
    sessions.sort(key=lambda x: x["created_at"], reverse=True)

    return sessions
```

Test endpoint:
```bash
# List last 7 days
curl http://localhost:8000/api/v1/sessions/recent

# List last 30 days, completed only
curl "http://localhost:8000/api/v1/sessions/recent?days=30&status=completed"
```

---

## Testing Your Changes

### Unit Tests

```python
# tests/test_mycomponent.py
import pytest
from app.components.mycomponent import MyService, MyRequest


@pytest.mark.asyncio
async def test_component_process():
    """Test component processing logic."""
    service = MyService()
    request = MyRequest(session_id="test", data="input")

    response = await service.process(request)

    assert response.session_id == "test"
    assert response.result is not None


def test_validation():
    """Test request validation."""
    with pytest.raises(ValueError):
        MyRequest(session_id="test", data="")  # Invalid: empty data
```

### Integration Tests

```python
# tests/integration/test_workflow.py
import pytest
from app.components.orchestrator.workflow import workflow


@pytest.mark.asyncio
async def test_full_workflow():
    """Test complete pipeline end-to-end."""
    initial_state = {
        "session_id": "integration_test",
        "requirement_text": "Build user authentication with OAuth2 support",
        "status": "created",
    }

    result = await workflow.ainvoke(initial_state)

    # Verify all agents ran
    assert result["status"] == "completed"
    assert "extracted_keywords" in result
    assert "all_matches" in result
    assert "tdd_output" in result
    assert "jira_stories_output" in result
```

### API Tests

```python
# tests/api/test_endpoints.py
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_create_session():
    """Test session creation endpoint."""
    response = client.post(
        "/api/v1/sessions",
        json={"created_by": "test_user"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "created"


def test_requirement_submission():
    """Test requirement submission endpoint."""
    # Create session first
    session_response = client.post(
        "/api/v1/sessions",
        json={"created_by": "test"}
    )
    session_id = session_response.json()["session_id"]

    # Submit requirement
    response = client.post(
        "/api/v1/requirement/submit",
        json={
            "session_id": session_id,
            "requirement_description": "Build authentication system with OAuth2 and JWT support",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["extracted_keywords"]) > 0
```

### Run All Tests

```bash
# All tests
pytest

# Specific category
pytest tests/unit/
pytest tests/integration/
pytest tests/api/

# With coverage
pytest --cov=app --cov-report=html

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

---

## Update Data Schema

**Goal:** Modify CSV schema for ChromaDB indexing.

### Step 1: Update CSV File

Edit `data/raw/epics.csv`, add new column:

```csv
epic_id,epic_name,description,technologies,actual_hours,complexity
EPIC-001,User Auth,OAuth implementation,"Python,FastAPI",240,high
```

### Step 2: Update Indexing Script

Edit `scripts/init_vector_db.py`:

```python
def index_epics():
    """Index epics with new complexity field."""
    df = pd.read_csv("data/raw/epics.csv")

    # ... existing code ...

    for _, row in df.iterrows():
        metadatas.append({
            "epic_id": row["epic_id"],
            "epic_name": row["epic_name"],
            "technologies": row["technologies"],
            "actual_hours": row["actual_hours"],
            "complexity": row.get("complexity", "medium"),  # ← Add this
        })
```

### Step 3: Reindex

```bash
# Backup existing
cp -r data/chroma data/chroma.backup

# Reindex
python scripts/reindex.py && python scripts/init_vector_db.py

# Verify
python -c "from app.rag.vector_store import VectorStoreManager; \
           store = VectorStoreManager.get_instance(); \
           coll = store.get_collection('epics'); \
           result = coll.get(limit=1); \
           print('Metadata:', result['metadatas'][0])"
```

---

## Add Configuration Options

**Goal:** Add new configurable settings.

### Step 1: Update Settings Class

Edit `app/components/base/config.py`:

```python
class Settings(BaseSettings):
    """Application settings."""

    # ... existing settings ...

    # New settings
    risk_assessment_enabled: bool = True
    max_concurrent_agents: int = 3
    cache_ttl_seconds: int = 3600

    class Config:
        env_file = ".env"
        env_prefix = ""  # No prefix for top-level vars
```

### Step 2: Add to `.env`

```bash
# Risk Assessment
RISK_ASSESSMENT_ENABLED=true
MAX_CONCURRENT_AGENTS=3
CACHE_TTL_SECONDS=3600
```

### Step 3: Use in Code

```python
from app.components.base.config import get_settings

settings = get_settings()

if settings.risk_assessment_enabled:
    # Run risk assessment
    pass
```

---

## See Also

- [README.md](../README.md) - Quick start guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Debug guide
- [Component READMEs](../app/components/) - Component docs
