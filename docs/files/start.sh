#!/bin/bash

# SDLC Full Stack Starter
# Starts both backend and frontend services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/ele-sdlc-backend"
FRONTEND_DIR="$SCRIPT_DIR/ele-sdlc-frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}        SDLC Development Stack Launcher          ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Function to check and start Ollama
check_ollama() {
    echo -e "\n${YELLOW}▶ Checking Ollama...${NC}"

    # Check if Ollama is installed
    if ! command -v ollama &> /dev/null; then
        echo -e "${RED}✗ Ollama is not installed${NC}"
        echo -e "  Install from: ${CYAN}https://ollama.ai${NC}"
        echo -e "  macOS: brew install ollama"
        return 1
    fi

    # Check if Ollama is running, start if not
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "  Starting Ollama server..."
        ollama serve > /dev/null 2>&1 &
        sleep 3
        if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo -e "${RED}✗ Failed to start Ollama${NC}"
            return 1
        fi
    fi
    echo -e "${GREEN}✓ Ollama is running${NC}"

    # Check for required models
    MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null || echo '{"models":[]}')

    if ! echo "$MODELS" | grep -q "all-minilm"; then
        echo -e "  ${YELLOW}Pulling all-minilm model (embeddings)...${NC}"
        ollama pull all-minilm
    fi

    if ! echo "$MODELS" | grep -q "phi3:mini"; then
        echo -e "  ${YELLOW}Pulling phi3:mini model (generation)...${NC}"
        ollama pull phi3:mini
    fi
    echo -e "${GREEN}✓ Required models available${NC}"
}

# Function to check ChromaDB
check_chromadb() {
    if [ ! -d "$BACKEND_DIR/data/chroma" ] || [ -z "$(ls -A "$BACKEND_DIR/data/chroma" 2>/dev/null)" ]; then
        echo -e "${YELLOW}⚠ ChromaDB not initialized${NC}"
        echo -e "  Run: ${CYAN}cd ele-sdlc-backend && python scripts/init_vector_db.py${NC}"
        echo -e "  Or use: ${CYAN}cd ele-sdlc-backend && ./start_dev.sh${NC} for interactive setup"
        return 1
    fi
    echo -e "${GREEN}✓ ChromaDB index exists${NC}"
}

# Function to start main backend
start_backend() {
    echo -e "\n${YELLOW}▶ Starting Main Backend (FastAPI/LangGraph)...${NC}"

    if [ ! -d "$BACKEND_DIR" ]; then
        echo -e "${RED}Error: Backend directory not found at $BACKEND_DIR${NC}"
        return 1
    fi

    # Pre-flight checks
    check_ollama || return 1
    check_chromadb || return 1

    cd "$BACKEND_DIR"

    # Activate virtual environment if it exists
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    elif [ -f "../.venv/bin/activate" ]; then
        source ../.venv/bin/activate
    fi

    # Start main backend in background
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/sdlc-backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/sdlc-backend.pid

    sleep 2
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Main Backend started (PID: $BACKEND_PID) on http://localhost:8000${NC}"
    else
        echo -e "${RED}✗ Main Backend failed to start. Check /tmp/sdlc-backend.log${NC}"
        return 1
    fi
}

# Function to start pipeline backend
start_pipeline() {
    echo -e "\n${YELLOW}▶ Starting Pipeline Backend (Data Engineering)...${NC}"

    if [ ! -d "$BACKEND_DIR" ]; then
        echo -e "${RED}Error: Backend directory not found at $BACKEND_DIR${NC}"
        return 1
    fi

    cd "$BACKEND_DIR"

    # Activate virtual environment (prefer parent .venv for complete dependencies)
    if [ -f "../.venv/bin/activate" ]; then
        source ../.venv/bin/activate
    elif [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi

    # Start pipeline backend in background (no reload to avoid subprocess import issues)
    nohup uvicorn pipeline.main:app --host 0.0.0.0 --port 8001 > /tmp/sdlc-pipeline.log 2>&1 &
    PIPELINE_PID=$!
    echo $PIPELINE_PID > /tmp/sdlc-pipeline.pid

    sleep 2
    if kill -0 $PIPELINE_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Pipeline Backend started (PID: $PIPELINE_PID) on http://localhost:8001${NC}"
    else
        echo -e "${RED}✗ Pipeline Backend failed to start. Check /tmp/sdlc-pipeline.log${NC}"
        return 1
    fi
}

# Function to start frontend
start_frontend() {
    echo -e "\n${YELLOW}▶ Starting Frontend (Next.js)...${NC}"

    if [ ! -d "$FRONTEND_DIR" ]; then
        echo "Error: Frontend directory not found at $FRONTEND_DIR"
        return 1
    fi

    cd "$FRONTEND_DIR"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi

    # Start frontend in background
    nohup npm run dev > /tmp/sdlc-frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > /tmp/sdlc-frontend.pid

    sleep 3
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID) on http://localhost:3000${NC}"
    else
        echo "✗ Frontend failed to start. Check /tmp/sdlc-frontend.log"
        return 1
    fi
}

# Parse arguments
case "${1:-all}" in
    backend)
        start_backend
        ;;
    pipeline)
        start_pipeline
        ;;
    frontend)
        start_frontend
        ;;
    all|*)
        start_backend
        start_pipeline
        start_frontend
        echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}Full stack is now running!${NC}"
        echo -e "  Main Backend:     http://localhost:8000"
        echo -e "  Pipeline Backend: http://localhost:8001"
        echo -e "  Frontend:         http://localhost:3000"
        echo -e "\n${CYAN}API Documentation:${NC}"
        echo -e "  Main API:     http://localhost:8000/docs"
        echo -e "  Pipeline API: http://localhost:8001/docs"
        echo -e "\n${CYAN}Logs:${NC}"
        echo -e "  Main Backend: tail -f /tmp/sdlc-backend.log"
        echo -e "  Pipeline:     tail -f /tmp/sdlc-pipeline.log"
        echo -e "  Frontend:     tail -f /tmp/sdlc-frontend.log"
        echo -e "\nTo stop: ${YELLOW}./stop.sh${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        ;;
esac
