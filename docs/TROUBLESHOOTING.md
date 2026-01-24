# Troubleshooting Guide

This guide helps diagnose and resolve common issues in the AI Impact Assessment System.

## Quick Diagnosis

Run these commands first to identify the problem area:

```bash
# 1. Check service health
curl http://localhost:8000/api/v1/health

# 2. Verify Ollama is running
curl http://localhost:11434/api/tags

# 3. Check ChromaDB collections
python -c "from app.rag.vector_store import VectorStoreManager; \
           store = VectorStoreManager.get_instance(); \
           print(store.list_collections())"

# 4. Check logs
tail -f logs/app.log  # If logging to file
# Or check console output if running with uvicorn --reload

# 5. Verify environment
cat .env
```

---

## Table of Contents

- [Ollama Issues](#ollama-issues)
- [ChromaDB Issues](#chromadb-issues)
- [LangGraph Issues](#langgraph-issues)
- [JSON Parsing](#json-parsing)
- [Session & Audit Trail](#session--audit-trail)
- [Performance Issues](#performance)
- [Deployment Issues](#deployment)
- [Debug Workflows](#debug-workflows)
- [Getting Help](#getting-help)

---

## Ollama Issues

### Symptom: `OllamaUnavailableError` - Connection refused

**Cause:** Ollama service not running or wrong URL

**Solution:**
```bash
# 1. Check if Ollama is running
curl http://localhost:11434/api/tags

# 2. If not running, start Ollama
# macOS/Linux:
ollama serve

# 3. Verify models are pulled
ollama list

# Expected output:
# NAME              ID              SIZE
# phi3:mini         abc123          2.3 GB
# all-minilm        def456          46 MB

# 4. If models missing, pull them
ollama pull phi3:mini
ollama pull all-minilm

# 5. Verify connection from Python
python -c "import requests; print(requests.get('http://localhost:11434/api/tags').status_code)"
# Expected: 200
```

**Environment Check:**
```bash
# Check your .env file
grep OLLAMA .env

# Should see:
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_GEN_MODEL=phi3:mini
# OLLAMA_EMBED_MODEL=all-minilm
```

---

### Symptom: `OllamaTimeoutError` - Request timeout after 120s

**Cause:** Model too large, insufficient resources, or complex prompt

**Solutions:**

1. **Use smaller model:**
   ```bash
   # Switch to phi3:mini (2.3GB) instead of llama3 (4.7GB)
   export OLLAMA_GEN_MODEL=phi3:mini
   ```

2. **Increase timeout:**
   ```bash
   export OLLAMA_TIMEOUT_SECONDS=300  # 5 minutes
   ```

3. **Check system resources:**
   ```bash
   # Monitor while running
   htop  # or top

   # Ollama should show high CPU usage during generation
   # If idle, model might be stuck
   ```

4. **Restart Ollama:**
   ```bash
   pkill ollama
   ollama serve
   ```

---

### Symptom: Low-quality LLM responses

**Cause:** Wrong temperature, model not suitable, or poor prompt

**Solutions:**

1. **Adjust temperature (0.0 = deterministic, 1.0 = creative):**
   ```bash
   # For structured outputs (JSON, lists)
   export OLLAMA_TEMPERATURE=0.1

   # For creative content (TDDs, stories)
   export OLLAMA_TEMPERATURE=0.5
   ```

2. **Try different model:**
   ```bash
   # More accurate but slower
   ollama pull llama3
   export OLLAMA_GEN_MODEL=llama3

   # Faster but less accurate
   export OLLAMA_GEN_MODEL=phi3:mini
   ```

3. **Review prompt templates:**
   ```bash
   # Check prompts in:
   ls app/components/*/prompts.py
   ```

---

## ChromaDB Issues

### Symptom: `VectorDBError` - Collection not found

**Cause:** Database not initialized or corrupted

**Solution:**
```bash
# 1. Check existing collections
python -c "from app.rag.vector_store import VectorStoreManager; \
           store = VectorStoreManager.get_instance(); \
           print('Collections:', store.list_collections())"

# Expected output: ['epics', 'estimations', 'tdds']

# 2. If missing, initialize database
python scripts/init_vector_db.py

# 3. Verify data files exist
ls data/raw/
# Should see: epics.csv, estimations.csv, tdds.csv

# 4. Check ChromaDB directory
ls -lh data/chroma/
```

---

### Symptom: No search results returned

**Cause:** Empty collections, wrong collection name, or poor embeddings

**Debug:**
```python
# Test script: test_search.py
from app.rag.vector_store import VectorStoreManager
from app.rag.embeddings import OllamaEmbeddingService

store = VectorStoreManager.get_instance()
embedding_service = OllamaEmbeddingService.get_instance()

# 1. Check collection size
collection = store.get_collection("epics")
print(f"Collection size: {collection.count()}")  # Should be > 0

# 2. Test embedding
query_embedding = embedding_service.embed_query("user authentication")
print(f"Embedding dimension: {len(query_embedding)}")  # Should be 384 for all-minilm

# 3. Manual search
results = collection.query(query_embeddings=[query_embedding], n_results=5)
print(f"Found {len(results['ids'][0])} results")
```

**Solutions:**

1. **Reindex if collection empty:**
   ```bash
   python scripts/reindex.py && python scripts/init_vector_db.py
   ```

2. **Verify embedding model:**
   ```bash
   ollama list | grep all-minilm
   ```

3. **Check data/raw/ CSV files have content:**
   ```bash
   wc -l data/raw/*.csv
   # Should see multiple lines for each file
   ```

---

### Symptom: ChromaDB permission denied

**Cause:** Incorrect permissions on data/chroma/ directory

**Solution:**
```bash
# Fix permissions
chmod -R 755 data/chroma/
chown -R $USER data/chroma/

# Or delete and reinitialize (destructive!)
rm -rf data/chroma/
python scripts/init_vector_db.py
```

---

## LangGraph Issues

### Symptom: Workflow infinite loop

**Cause:** Agent returns same `current_agent` indefinitely

**Debug:**
```python
# Check workflow edges in app/components/orchestrator/workflow.py
# Ensure each node sets correct next agent

# Example problematic pattern:
async def my_agent(state):
    return {
        "status": "processing",
        "current_agent": "my_agent",  # ❌ Points to itself!
    }

# Correct pattern:
async def my_agent(state):
    return {
        "status": "completed",
        "current_agent": "next_agent",  # ✅ Moves forward
    }
```

**Solution:**
```bash
# 1. Review workflow graph
python -c "from app.components.orchestrator.workflow import workflow; \
           print(workflow.get_graph().edges)"

# 2. Check session audit trail for loop
ls sessions/*/sess_*/step3_agents/
# If you see repeated agent_xxx directories, loop detected

# 3. Add max_steps limit in workflow execution
# In orchestrator/workflow.py:
# workflow.run(state, max_steps=20)  # Prevent infinite loops
```

---

### Symptom: Agent skipped in workflow

**Cause:** Conditional edges not configured or wrong status

**Debug:**
```python
# Check state transitions in workflow.py
# Ensure status values match edge conditions

# Example:
workflow.add_conditional_edges(
    "search",
    lambda state: state.get("status"),
    {
        "matches_found": "auto_select",  # ✅ Agent sets this status
        "no_matches": "END",
    }
)

# If agent returns different status, edge won't match
async def search_agent(state):
    return {
        "status": "search_complete",  # ❌ Doesn't match any edge!
    }
```

**Solution:**
- Review `app/components/orchestrator/state.py` for valid status values
- Ensure agents return expected status strings
- Check workflow edges in `workflow.py`

---

### Symptom: State not updating

**Cause:** Agent not returning partial state update

**Debug:**
```python
# ❌ Wrong: Full state replacement
async def my_agent(state):
    new_state = {
        "session_id": state["session_id"],
        "my_output": "result",
    }
    return new_state  # Loses all other state fields!

# ✅ Correct: Partial update
async def my_agent(state):
    return {
        "my_output": "result",  # Only changed fields
    }
```

---

## JSON Parsing

### Symptom: `ResponseParsingError` - Failed to parse LLM JSON

**Cause:** Malformed JSON from LLM (common with smaller models)

**Solution:**

The system already uses `app/utils/json_repair.py` to handle common issues. If still failing:

```python
# 1. Check raw LLM response in audit trail
cat sessions/*/sess_*/step3_agents/agent_xxx/raw_response.txt

# Common issues:
# - Trailing commas: {"key": "value",}
# - Unquoted keys: {key: "value"}
# - Truncated JSON: {"key": "val
# - Extra text: "Here's the JSON: {...}"

# 2. Manually test json_repair
python -c "from app.utils.json_repair import parse_llm_json; \
           result = parse_llm_json('{\"key\": \"value\",}'); \
           print(result)"

# 3. If still failing, adjust prompt to request simpler structure
# Edit app/components/*/prompts.py:
# - Request shorter responses
# - Use specific JSON schema examples
# - Add "Return ONLY valid JSON, no extra text" instruction
```

---

### Symptom: Empty or missing fields in parsed JSON

**Cause:** LLM not following JSON schema

**Debug:**
```python
# Check prompt template in app/components/*/prompts.py
# Ensure it includes clear schema example

# ❌ Weak prompt:
"Return the modules in JSON format"

# ✅ Strong prompt:
"""Return modules in this EXACT JSON format:
{
  "modules": [
    {"name": "auth", "impact": "high", "reason": "..."}
  ]
}
"""

# Also check Pydantic model validation
# In app/components/*/models.py:
from pydantic import Field

class Module(BaseModel):
    name: str = Field(..., min_length=1)  # Prevent empty
    impact: str = Field(..., pattern="^(high|medium|low)$")  # Enum
```

---

## Session & Audit Trail

### Symptom: Audit files not created

**Cause:** Permission issues or missing directory

**Solution:**
```bash
# 1. Check sessions directory exists and is writable
ls -ld sessions/
chmod 755 sessions/

# 2. Test audit trail creation
python -c "from app.utils.audit import AuditTrailManager; \
           audit = AuditTrailManager('test_session'); \
           audit.save_json('test.json', {'test': 'data'}); \
           print('Success')"

# 3. Verify file created
ls sessions/*/test_session/

# 4. Check for disk space
df -h .
```

---

### Symptom: Session ID collision

**Cause:** Multiple sessions created in same millisecond

**Solution:**
```python
# Rare issue - ID includes timestamp + random suffix
# If occurs, adjust id_generator.py to add longer random suffix

# Check current format
python -c "from app.utils.id_generator import generate_session_id; \
           print(generate_session_id())"
# Format: sess_YYYYMMDD_HHMMSS_RANDOM
```

---

## Performance

### Symptom: Slow API response (>30 seconds)

**Diagnosis:**
```bash
# 1. Check which agent is slow via audit trail timing
python -c "from app.utils.audit import AuditTrailManager; \
           audit = AuditTrailManager('sess_xxx'); \
           timings = audit.get_timings(); \
           print(timings)"

# 2. Common slow operations:
# - LLM generation: 5-15s per agent (normal)
# - Search: <1s (if slow, index issue)
# - File I/O: <100ms (if slow, disk issue)
```

**Solutions:**

| Slow Operation | Solution |
|----------------|----------|
| LLM generation (>15s per agent) | Use `phi3:mini` instead of `llama3` |
| Search (>5s) | Reduce `SEARCH_MAX_RESULTS` to 10 |
| Multiple agents (~60s total) | Expected; use async or streaming |
| File upload (>10s) | Check network, limit file size |

**Optimization tips:**
```bash
# 1. Use smaller, faster models
export OLLAMA_GEN_MODEL=phi3:mini  # 3x faster than llama3

# 2. Reduce search scope
export SEARCH_MAX_RESULTS=10

# 3. Enable ChromaDB persistence (skip reindexing)
export CHROMA_PERSIST_DIR=./data/chroma

# 4. Monitor with profiling
python -m cProfile -o output.prof app/main.py
```

---

### Symptom: High memory usage (>4GB)

**Cause:** Large model loaded, or vector index in memory

**Solutions:**
```bash
# 1. Use smaller model
ollama pull phi3:mini  # 2.3GB vs llama3 4.7GB

# 2. Limit collection size
# Only index recent data (edit scripts/init_vector_db.py)

# 3. Monitor memory
ps aux | grep ollama
ps aux | grep uvicorn
```

---

## Deployment

### Symptom: Import errors in production

**Cause:** Missing dependencies or wrong Python version

**Solution:**
```bash
# 1. Verify Python version
python --version  # Should be 3.10+

# 2. Reinstall dependencies
pip install -r requirements.txt --no-cache-dir

# 3. Check for missing packages
python -c "import fastapi, langgraph, chromadb, ollama, pydantic; print('OK')"

# 4. Verify PYTHONPATH
echo $PYTHONPATH
export PYTHONPATH=/path/to/ele-sdlc-backend:$PYTHONPATH
```

---

### Symptom: Environment variables not loaded

**Cause:** `.env` file not in working directory

**Solution:**
```bash
# 1. Verify .env location
ls -la .env

# 2. Check it's loaded
python -c "from app.components.base.config import get_settings; \
           settings = get_settings(); \
           print(f'Model: {settings.ollama_gen_model}')"

# 3. Explicitly load .env
export $(cat .env | xargs)

# 4. Or use absolute path
export ENV_FILE=/path/to/ele-sdlc-backend/.env
```

---

## Debug Workflows

### Complete Diagnostic Script

Save as `debug_system.sh`:

```bash
#!/bin/bash
echo "=== System Diagnostics ==="
echo ""

echo "1. Python version:"
python --version
echo ""

echo "2. Ollama status:"
curl -s http://localhost:11434/api/tags | head -5
echo ""

echo "3. Ollama models:"
ollama list
echo ""

echo "4. API health:"
curl -s http://localhost:8000/api/v1/health | python -m json.tool
echo ""

echo "5. ChromaDB collections:"
python -c "from app.rag.vector_store import VectorStoreManager; \
           store = VectorStoreManager.get_instance(); \
           print(store.list_collections())"
echo ""

echo "6. Data files:"
ls -lh data/raw/
echo ""

echo "7. Recent sessions:"
ls -lt sessions/ | head -10
echo ""

echo "8. Disk space:"
df -h .
echo ""

echo "9. Memory usage:"
ps aux | grep -E '(ollama|uvicorn)' | grep -v grep
echo ""

echo "=== Diagnostics Complete ==="
```

Run with:
```bash
chmod +x debug_system.sh
./debug_system.sh > diagnostics.txt
```

---

### Agent-Specific Debugging

```python
# test_agent.py - Test individual agent
import asyncio
from app.components.tdd.agent import tdd_agent  # or any agent
from app.components.orchestrator.state import State

async def test():
    # Minimal state
    state = {
        "session_id": "test_session",
        "requirement_text": "Build user authentication system",
        "selected_matches": [...],  # Add required fields
        "status": "matches_selected",
    }

    try:
        result = await tdd_agent(state)
        print("✅ Agent succeeded")
        print(f"Status: {result.get('status')}")
        print(f"Output keys: {result.keys()}")
    except Exception as e:
        print(f"❌ Agent failed: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
```

---

## Getting Help

### Collect Debug Information

Before reporting issues, collect:

```bash
# 1. Run diagnostics
./debug_system.sh > diagnostics.txt

# 2. Get recent logs
tail -100 logs/app.log > recent_logs.txt  # if logging to file

# 3. Get session audit trail (replace sess_xxx with actual ID)
tar -czf session_audit.tar.gz sessions/*/sess_xxx/

# 4. Export configuration (sanitize secrets!)
env | grep -E '(OLLAMA|CHROMA|SEARCH)' > config.txt

# 5. Get system info
uname -a > system_info.txt
python --version >> system_info.txt
pip list >> system_info.txt
```

### Enable Debug Logging

```bash
# Set in .env or export
export LOG_LEVEL=DEBUG

# Restart server
./stop_dev.sh
./start_dev.sh

# Or with uvicorn directly
uvicorn app.main:app --log-level debug
```

---

## Common Error Messages Reference

| Error Message | Component | Fix Link |
|---------------|-----------|----------|
| `OllamaUnavailableError` | Ollama | [Ollama Issues](#ollama-issues) |
| `VectorDBError` | ChromaDB | [ChromaDB Issues](#chromadb-issues) |
| `ResponseParsingError` | JSON | [JSON Parsing](#json-parsing) |
| `RequirementTooShortError` | Requirement | Provide 20+ character requirement |
| `SessionNotFoundError` | Session | Create session first with POST /sessions |
| `NoMatchesFoundError` | Search | Check ChromaDB initialized |
| `AgentExecutionError` | LangGraph | [LangGraph Issues](#langgraph-issues) |

---

## Prevention Checklist

Before deploying or making changes:

- [ ] Run `pytest -v` - All tests pass
- [ ] Run `./debug_system.sh` - All services healthy
- [ ] Test full pipeline with sample requirement
- [ ] Check audit trail created correctly
- [ ] Verify search returns results
- [ ] Monitor first 10 requests in production
- [ ] Review error logs for patterns
- [ ] Ensure `.env` configured for environment

---

## See Also

- [README.md](../README.md) - Quick start and overview
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design details
- [HOW_TO_GUIDE.md](HOW_TO_GUIDE.md) - Development recipes
- [Component READMEs](../app/components/) - Component-specific docs
