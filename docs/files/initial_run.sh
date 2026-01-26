#!/bin/bash
set -e

# ═══════════════════════════════════════════════════════════════
# AI Impact Assessment System - Initial Setup Script
# ═══════════════════════════════════════════════════════════════
# This script sets up everything needed to run the SDLC system
# on a fresh machine. Run this once before using start.sh.
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
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

# ═══════════════════════════════════════════════════════════════
# Header
# ═══════════════════════════════════════════════════════════════
clear
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}                                                            ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}   ${BOLD}${CYAN}AI Impact Assessment System${NC}                             ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}   ${DIM}Initial Setup for Fresh Installation${NC}                    ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}                                                            ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${DIM}This script will set up all dependencies and configuration${NC}"
echo -e "${DIM}needed to run the SDLC system on a fresh machine.${NC}"
echo ""
echo -e "${YELLOW}Press Enter to continue or Ctrl+C to abort...${NC}"
read

# ═══════════════════════════════════════════════════════════════
# Step 1: Prerequisites Check
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}┌────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC} ${BOLD}[1/8] Prerequisites Check${NC}                                  ${BLUE}│${NC}"
echo -e "${BLUE}└────────────────────────────────────────────────────────────┘${NC}"
echo ""

PREREQ_FAILED=0

# Check Git
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version | cut -d' ' -f3)
    echo -e "      ${CHECK} Git ${DIM}(version $GIT_VERSION)${NC}"
else
    echo -e "      ${CROSS} Git not found"
    echo -e "         ${ARROW} Install: ${CYAN}https://git-scm.com/${NC}"
    PREREQ_FAILED=1
fi

# Check Python 3.10+
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        echo -e "      ${CHECK} Python ${DIM}(version $PYTHON_VERSION)${NC}"
    else
        echo -e "      ${CROSS} Python 3.10+ required ${DIM}(found $PYTHON_VERSION)${NC}"
        PREREQ_FAILED=1
    fi
else
    echo -e "      ${CROSS} Python 3 not found"
    echo -e "         ${ARROW} Install: ${CYAN}https://www.python.org/downloads/${NC}"
    PREREQ_FAILED=1
fi

# Check Node.js 18+
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | cut -d'v' -f2)
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1)
    if [ "$NODE_MAJOR" -ge 18 ]; then
        echo -e "      ${CHECK} Node.js ${DIM}(version $NODE_VERSION)${NC}"
    else
        echo -e "      ${CROSS} Node.js 18+ required ${DIM}(found $NODE_VERSION)${NC}"
        PREREQ_FAILED=1
    fi
else
    echo -e "      ${CROSS} Node.js not found"
    echo -e "         ${ARROW} Install: ${CYAN}https://nodejs.org/${NC}"
    PREREQ_FAILED=1
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo -e "      ${CHECK} npm ${DIM}(version $NPM_VERSION)${NC}"
else
    echo -e "      ${CROSS} npm not found ${DIM}(comes with Node.js)${NC}"
    PREREQ_FAILED=1
fi

# Check curl
if command -v curl &> /dev/null; then
    echo -e "      ${CHECK} curl"
else
    echo -e "      ${CROSS} curl not found"
    PREREQ_FAILED=1
fi

if [ $PREREQ_FAILED -eq 1 ]; then
    echo ""
    echo -e "${RED}Prerequisites check failed. Please install missing dependencies.${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}All prerequisites satisfied!${NC}"

# ═══════════════════════════════════════════════════════════════
# Step 2: Install Ollama
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}┌────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC} ${BOLD}[2/8] Ollama Installation${NC}                                  ${BLUE}│${NC}"
echo -e "${BLUE}└────────────────────────────────────────────────────────────┘${NC}"
echo ""

if command -v ollama &> /dev/null; then
    echo -e "      ${CHECK} Ollama already installed"
else
    echo -e "      ${WARN} Ollama not found"
    echo ""
    echo -e "      Ollama is required for local LLM inference."
    echo -e "      Visit: ${CYAN}https://ollama.ai${NC}"
    echo ""

    # Detect OS and provide specific instructions
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "      ${ARROW} ${BOLD}macOS Installation:${NC}"
        echo -e "         Option 1: ${CYAN}brew install ollama${NC}"
        echo -e "         Option 2: Download from https://ollama.ai"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo -e "      ${ARROW} ${BOLD}Linux Installation:${NC}"
        echo -e "         ${CYAN}curl -fsSL https://ollama.ai/install.sh | sh${NC}"
    else
        echo -e "      ${ARROW} ${BOLD}Windows:${NC}"
        echo -e "         Download installer from https://ollama.ai"
    fi

    echo ""
    echo -e "${YELLOW}Please install Ollama and run this script again.${NC}"
    exit 1
fi

# ═══════════════════════════════════════════════════════════════
# Step 3: Start Ollama and Pull Models
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}┌────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC} ${BOLD}[3/8] Ollama Models Setup${NC}                                  ${BLUE}│${NC}"
echo -e "${BLUE}└────────────────────────────────────────────────────────────┘${NC}"
echo ""

# Check if Ollama is running, start if not
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "      ${ARROW} Starting Ollama server..."
    ollama serve > /dev/null 2>&1 &
    OLLAMA_PID=$!

    # Wait for Ollama to be ready
    echo -ne "      ${ARROW} Waiting for Ollama to be ready"
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo -e "\r      ${CHECK} Ollama started ${DIM}(PID: $OLLAMA_PID)${NC}           "
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

# Pull required models
MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null || echo '{"models":[]}')

echo -e "      ${ARROW} Checking required models..."
echo ""

# Embedding model (all-minilm)
if ! echo "$MODELS" | grep -q "all-minilm"; then
    echo -e "      ${WARN} Pulling ${CYAN}all-minilm${NC} ${DIM}(~45MB, for embeddings)${NC}"
    ollama pull all-minilm
    echo -e "      ${CHECK} Embedding model ready"
else
    echo -e "      ${CHECK} ${CYAN}all-minilm${NC} ${DIM}(embeddings)${NC} already available"
fi

# Generation model (llama3.1)
if ! echo "$MODELS" | grep -q "llama3.1"; then
    echo -e "      ${WARN} Pulling ${CYAN}llama3.1:latest${NC} ${DIM}(~4.7GB, for generation)${NC}"
    echo -e "      ${DIM}This may take several minutes...${NC}"
    ollama pull llama3.1:latest
    echo -e "      ${CHECK} Generation model ready"
else
    echo -e "      ${CHECK} ${CYAN}llama3.1${NC} ${DIM}(generation)${NC} already available"
fi

# ═══════════════════════════════════════════════════════════════
# Step 4: Python Virtual Environment
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}┌────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC} ${BOLD}[4/8] Python Virtual Environment${NC}                           ${BLUE}│${NC}"
echo -e "${BLUE}└────────────────────────────────────────────────────────────┘${NC}"
echo ""

VENV_DIR="$SCRIPT_DIR/.venv"

if [ -d "$VENV_DIR" ]; then
    echo -e "      ${CHECK} Virtual environment already exists"
else
    echo -e "      ${ARROW} Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo -e "      ${CHECK} Virtual environment created"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
echo -e "      ${CHECK} Virtual environment activated"

# Upgrade pip
echo -e "      ${ARROW} Upgrading pip..."
pip install --quiet --upgrade pip
echo -e "      ${CHECK} pip upgraded"

# ═══════════════════════════════════════════════════════════════
# Step 5: Install Python Dependencies
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}┌────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC} ${BOLD}[5/8] Python Dependencies${NC}                                  ${BLUE}│${NC}"
echo -e "${BLUE}└────────────────────────────────────────────────────────────┘${NC}"
echo ""

cd "$SCRIPT_DIR/ele-sdlc-backend"

if [ -f "requirements.txt" ]; then
    echo -e "      ${ARROW} Installing backend dependencies..."
    echo -e "      ${DIM}This may take a few minutes...${NC}"

    # Use uv if available (faster), otherwise fall back to pip
    if command -v uv &> /dev/null; then
        echo -e "      ${CHECK} Using ${CYAN}uv${NC} for faster installation"
        uv pip install -r requirements.txt
    else
        echo -e "      ${WARN} uv not found, using pip ${DIM}(install uv for faster installs: pip install uv)${NC}"
        pip install --quiet -r requirements.txt
    fi
    echo -e "      ${CHECK} Backend dependencies installed"
else
    echo -e "      ${CROSS} requirements.txt not found"
    exit 1
fi

cd "$SCRIPT_DIR"

# ═══════════════════════════════════════════════════════════════
# Step 6: Backend Environment Configuration
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}┌────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC} ${BOLD}[6/8] Backend Environment Configuration${NC}                    ${BLUE}│${NC}"
echo -e "${BLUE}└────────────────────────────────────────────────────────────┘${NC}"
echo ""

BACKEND_ENV="$SCRIPT_DIR/ele-sdlc-backend/.env"
BACKEND_ENV_EXAMPLE="$SCRIPT_DIR/ele-sdlc-backend/.env.example"

if [ -f "$BACKEND_ENV" ]; then
    echo -e "      ${CHECK} .env file already exists"
    echo -e "      ${DIM}To reconfigure, edit: ${CYAN}ele-sdlc-backend/.env${NC}"
else
    if [ -f "$BACKEND_ENV_EXAMPLE" ]; then
        echo -e "      ${ARROW} Creating .env file from template..."
        cp "$BACKEND_ENV_EXAMPLE" "$BACKEND_ENV"
        echo -e "      ${CHECK} .env file created from .env.example"
        echo ""
        echo -e "      ${DIM}Configuration summary:${NC}"
        echo -e "      ${DIM}- Generation model: llama3.1:latest (local Ollama)${NC}"
        echo -e "      ${DIM}- Embedding model: all-minilm (local Ollama)${NC}"
        echo -e "      ${DIM}- Context allocation: 40% requirement, 40% historical, 20% system${NC}"
        echo ""
        echo -e "      ${DIM}To customize settings, edit: ${CYAN}ele-sdlc-backend/.env${NC}"
    else
        echo -e "      ${WARN} .env.example not found, creating default .env..."
        cat > "$BACKEND_ENV" << 'EOF'
# Application
APP_ENV=development
DEBUG=true

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_GEN_MODEL=llama3.1:latest
OLLAMA_EMBED_MODEL=all-minilm
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_TEMPERATURE=0.3
OLLAMA_MAX_TOKENS=4096

# Debug: Set to true to disable JSON repair and see raw LLM output
JSON_REPAIR_DISABLED=false

# Prompt Management (context allocation ratios)
PROMPT_SYSTEM_RATIO=0.20
PROMPT_REQUIREMENT_RATIO=0.40
PROMPT_HISTORICAL_RATIO=0.40
PROMPT_OUTPUT_RESERVE=0.15

# ChromaDB
CHROMA_PERSIST_DIR=./data/chroma

# Search Weights
SEARCH_SEMANTIC_WEIGHT=0.70
SEARCH_KEYWORD_WEIGHT=0.30
SEARCH_MAX_RESULTS=10

# Paths
DATA_RAW_PATH=./data/raw
DATA_UPLOADS_PATH=./data/uploads
DATA_SESSIONS_PATH=./sessions

# Server
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
EOF
        echo -e "      ${CHECK} Default .env created"
    fi
fi

# ═══════════════════════════════════════════════════════════════
# Step 7: Install Frontend Dependencies
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}┌────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC} ${BOLD}[7/8] Frontend Dependencies${NC}                                ${BLUE}│${NC}"
echo -e "${BLUE}└────────────────────────────────────────────────────────────┘${NC}"
echo ""

cd "$SCRIPT_DIR/ele-sdlc-frontend"

if [ -f "package.json" ]; then
    if [ -d "node_modules" ]; then
        echo -e "      ${CHECK} Frontend dependencies already installed"
    else
        echo -e "      ${ARROW} Installing frontend dependencies..."
        echo -e "      ${DIM}This may take a few minutes...${NC}"
        npm install
        echo -e "      ${CHECK} Frontend dependencies installed"
    fi
else
    echo -e "      ${CROSS} package.json not found"
    exit 1
fi

cd "$SCRIPT_DIR"

# ═══════════════════════════════════════════════════════════════
# Step 8: Initialize ChromaDB Vector Database
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}┌────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC} ${BOLD}[8/8] ChromaDB Vector Database${NC}                             ${BLUE}│${NC}"
echo -e "${BLUE}└────────────────────────────────────────────────────────────┘${NC}"
echo ""

cd "$SCRIPT_DIR/ele-sdlc-backend"

# Re-activate virtual environment (in case we're in a subshell)
source "$SCRIPT_DIR/.venv/bin/activate"

CHROMA_DIR="$SCRIPT_DIR/ele-sdlc-backend/data/chroma"

if [ -d "$CHROMA_DIR" ] && [ -n "$(ls -A "$CHROMA_DIR" 2>/dev/null)" ]; then
    echo -e "      ${CHECK} ChromaDB index already exists"
    COLLECTION_COUNT=$(ls -d "$CHROMA_DIR"/*/ 2>/dev/null | wc -l | tr -d ' ')
    echo -e "      ${DIM}Collections found: $COLLECTION_COUNT${NC}"
else
    echo -e "      ${WARN} ChromaDB index not found"
    echo ""
    echo -e "      ${BOLD}Initialize vector database now?${NC}"
    echo -e "      ${DIM}This will index: epics, estimations, TDDs, stories, code${NC}"
    echo -e "      ${DIM}Required for historical match search functionality${NC}"
    echo ""
    echo -e "      ${CYAN}[Y]${NC} Yes, initialize now ${DIM}(recommended)${NC}"
    echo -e "      ${CYAN}[N]${NC} No, skip (can do later with: cd ele-sdlc-backend && python scripts/init_vector_db.py)"
    echo ""
    read -p "      Your choice [Y/n]: " INIT_CHOICE
    INIT_CHOICE=${INIT_CHOICE:-Y}

    if [[ "$INIT_CHOICE" =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "      ${ARROW} Initializing vector database..."
        echo -e "      ${DIM}This may take a few minutes...${NC}"
        echo ""
        python scripts/init_vector_db.py
        echo ""
        echo -e "      ${CHECK} Vector database initialized"
    else
        echo ""
        echo -e "      ${WARN} Skipping vector database initialization"
        echo -e "      ${DIM}You can initialize later with:${NC}"
        echo -e "      ${CYAN}cd ele-sdlc-backend && python scripts/init_vector_db.py${NC}"
    fi
fi

cd "$SCRIPT_DIR"

# ═══════════════════════════════════════════════════════════════
# Completion Summary
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}${GREEN}Setup Complete!${NC}                                            ${GREEN}║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}What was installed:${NC}                                       ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${CHECK} Ollama with all-minilm and llama3.1 models           ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${CHECK} Python virtual environment with dependencies          ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${CHECK} Backend environment configuration (.env)              ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${CHECK} Frontend Node.js dependencies                         ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${CHECK} ChromaDB vector database (if initialized)            ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}Next Steps:${NC}                                               ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  1. Verify .env configuration:                             ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}     ${CYAN}cat ele-sdlc-backend/.env${NC}                              ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  2. Start the full stack:                                  ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}     ${CYAN}./start.sh${NC}                                              ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  3. Access the application:                                ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}     Frontend:   ${CYAN}http://localhost:3000${NC}                      ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}     Backend:    ${CYAN}http://localhost:8000${NC}                      ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}     API Docs:   ${CYAN}http://localhost:8000/docs${NC}                 ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}     Pipeline:   ${CYAN}http://localhost:8001${NC}                      ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}Helpful Commands:${NC}                                         ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}     ${CYAN}./start.sh${NC}           Start all services                ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}     ${CYAN}./start.sh backend${NC}   Start backend only                ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}     ${CYAN}./start.sh frontend${NC}  Start frontend only               ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}     ${CYAN}./stop.sh${NC}            Stop all services                 ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}${GREEN}${ROCKET} Ready to launch! Run ${CYAN}./start.sh${GREEN} to begin.${NC}"
echo ""
