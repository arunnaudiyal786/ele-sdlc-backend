#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'
DIM='\033[2m'

# Symbols
CHECK="${GREEN}✓${NC}"
CROSS="${RED}✗${NC}"
ARROW="${CYAN}➜${NC}"
WARN="${YELLOW}⚠${NC}"
ROCKET="${MAGENTA}🚀${NC}"
GEAR="${CYAN}⚙${NC}"
DATABASE="${BLUE}🗄${NC}"
BRAIN="${MAGENTA}🧠${NC}"

# ═══════════════════════════════════════════════════════════════
# Header
# ═══════════════════════════════════════════════════════════════
clear
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}                                                            ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}   ${BOLD}${CYAN}AI Impact Assessment System${NC}                             ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}   ${DIM}SDLC Knowledge Base Backend${NC}                              ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}                                                            ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${DIM}Starting development environment...${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════
# Step 1: Check and Start Ollama
# ═══════════════════════════════════════════════════════════════
echo -e "${BLUE}┌────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC} ${BRAIN} ${BOLD}[1/4] Ollama LLM Runtime${NC}                                  ${BLUE}│${NC}"
echo -e "${BLUE}└────────────────────────────────────────────────────────────┘${NC}"

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo -e "      ${CROSS} ${RED}Ollama is not installed${NC}"
    echo ""
    echo -e "      ${ARROW} Install Ollama from: ${CYAN}https://ollama.ai${NC}"
    echo -e "      ${ARROW} macOS: ${DIM}brew install ollama${NC}"
    echo ""
    exit 1
fi
echo -e "      ${CHECK} Ollama installed"

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "      ${ARROW} Starting Ollama server..."
    ollama serve > /dev/null 2>&1 &
    OLLAMA_PID=$!
    echo -e "      ${CHECK} Ollama started ${DIM}(PID: $OLLAMA_PID)${NC}"

    # Wait for Ollama to be ready with spinner
    echo -ne "      ${ARROW} Waiting for Ollama to be ready"
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo -e "\r      ${CHECK} Ollama is ready!                    "
            break
        fi
        echo -ne "."
        sleep 1
        if [ $i -eq 30 ]; then
            echo -e "\r      ${CROSS} Ollama failed to start in time      "
            exit 1
        fi
    done
else
    echo -e "      ${CHECK} Ollama already running"
fi
echo ""

# ═══════════════════════════════════════════════════════════════
# Step 2: Pull Required Models
# ═══════════════════════════════════════════════════════════════
echo -e "${BLUE}┌────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC} ${GEAR} ${BOLD}[2/4] Ollama Models${NC}                                        ${BLUE}│${NC}"
echo -e "${BLUE}└────────────────────────────────────────────────────────────┘${NC}"

MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null || echo '{"models":[]}')

# Check embedding model
echo -e "      ${ARROW} Checking embedding model..."
if ! echo "$MODELS" | grep -q "all-minilm"; then
    echo -e "      ${WARN} Pulling ${CYAN}all-minilm${NC} ${DIM}(~45MB, for vector embeddings)${NC}"
    ollama pull all-minilm
    echo -e "      ${CHECK} Embedding model ready"
else
    echo -e "      ${CHECK} ${CYAN}all-minilm${NC} ${DIM}(embeddings)${NC} available"
fi

# Check generation model
echo -e "      ${ARROW} Checking generation model..."
if ! echo "$MODELS" | grep -q "phi3:mini"; then
    echo -e "      ${WARN} Pulling ${CYAN}phi3:mini${NC} ${DIM}(~2GB, for text generation)${NC}"
    ollama pull phi3:mini
    echo -e "      ${CHECK} Generation model ready"
else
    echo -e "      ${CHECK} ${CYAN}phi3:mini${NC} ${DIM}(generation)${NC} available"
fi
echo ""

# ═══════════════════════════════════════════════════════════════
# Step 3: Initialize Vector Database
# ═══════════════════════════════════════════════════════════════
echo -e "${BLUE}┌────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC} ${DATABASE} ${BOLD}[3/4] ChromaDB Vector Store${NC}                              ${BLUE}│${NC}"
echo -e "${BLUE}└────────────────────────────────────────────────────────────┘${NC}"

if [ ! -d "./data/chroma" ] || [ -z "$(ls -A ./data/chroma 2>/dev/null)" ]; then
    echo -e "      ${ARROW} Initializing vector database..."
    echo -e "      ${DIM}   Loading: epics, estimations, TDDs, stories, code${NC}"
    echo ""
    python scripts/init_vector_db.py
    echo ""
    echo -e "      ${CHECK} Vector database initialized"
else
    # Count collections
    COLLECTION_COUNT=$(ls -d ./data/chroma/*/ 2>/dev/null | wc -l | tr -d ' ')
    echo -e "      ${CHECK} ChromaDB already initialized"
    echo -e "      ${DIM}   Location: ./data/chroma${NC}"
    echo -e "      ${DIM}   Collections: ${COLLECTION_COUNT} indexed${NC}"
    echo ""
    echo -e "      ${WARN} To rebuild: ${CYAN}python scripts/reindex.py && python scripts/init_vector_db.py${NC}"
fi
echo ""

# ═══════════════════════════════════════════════════════════════
# Step 4: Start API Server
# ═══════════════════════════════════════════════════════════════
echo -e "${BLUE}┌────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC} ${ROCKET} ${BOLD}[4/4] FastAPI Server${NC}                                      ${BLUE}│${NC}"
echo -e "${BLUE}└────────────────────────────────────────────────────────────┘${NC}"
echo ""

# Summary box before starting
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}${GREEN}All Systems Ready!${NC}                                        ${GREEN}║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}API Server${NC}      ${CYAN}http://localhost:8000${NC}                   ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}Swagger Docs${NC}    ${CYAN}http://localhost:8000/docs${NC}              ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}Health Check${NC}    ${CYAN}http://localhost:8000/api/v1/health${NC}     ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}  ${DIM}Press ${BOLD}Ctrl+C${NC}${DIM} to stop the server${NC}                          ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${DIM}Run ${BOLD}./stop_dev.sh${NC}${DIM} to stop all services${NC}                   ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Start uvicorn with nice output
echo -e "${DIM}─────────────────────────── Server Logs ───────────────────────${NC}"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
