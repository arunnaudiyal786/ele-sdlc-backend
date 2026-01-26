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
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   AI Impact Assessment - Development Launcher   ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}This script will:${NC}"
echo -e "  ${DIM}1. Verify environment configuration (.env files)${NC}"
echo -e "  ${DIM}2. Setup Python virtual environment${NC}"
echo -e "  ${DIM}3. Check and start Ollama with required models${NC}"
echo -e "  ${DIM}4. Generate epic.csv from project folders${NC}"
echo -e "  ${DIM}5. Verify project data structure (epic.csv + project folders)${NC}"
echo -e "  ${DIM}6. Initialize/rebuild ChromaDB vector store${NC}"
echo -e "  ${DIM}7. Start backend and frontend services${NC}"
echo ""

# Function to check environment files
check_env_files() {
    echo -e "\n${YELLOW}▶ Checking Environment Configuration...${NC}"

    # Check backend .env
    if [ ! -f "$BACKEND_DIR/.env" ]; then
        echo -e "  ${YELLOW}⚠ Backend .env file not found${NC}"
        if [ -f "$BACKEND_DIR/.env.example" ]; then
            echo -e "\n  ${BOLD}Create .env file from template?${NC}"
            echo -e "  ${DIM}Required for backend configuration${NC}"
            echo -e "\n  ${CYAN}[Y]${NC} Yes, copy .env.example to .env ${DIM}(recommended)${NC}"
            echo -e "  ${CYAN}[N]${NC} No, skip"
            echo ""
            read -p "  Your choice [Y/n]: " CREATE_ENV
            CREATE_ENV=${CREATE_ENV:-Y}

            if [[ "$CREATE_ENV" =~ ^[Yy]$ ]]; then
                cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
                echo -e "  ${GREEN}✓ Created .env file from template${NC}"
                echo -e "  ${CYAN}You may want to review and customize: $BACKEND_DIR/.env${NC}"
            else
                echo -e "  ${YELLOW}⚠ Proceeding without .env (using defaults)${NC}"
            fi
        else
            echo -e "  ${YELLOW}⚠ No .env.example template found${NC}"
            echo -e "  ${DIM}Backend will use default configuration${NC}"
        fi
    else
        echo -e "${GREEN}✓ Backend .env file exists${NC}"
    fi

    # Check frontend .env.local
    if [ ! -f "$FRONTEND_DIR/.env.local" ]; then
        echo -e "  ${YELLOW}⚠ Frontend .env.local not found${NC}"
        echo -e "  ${DIM}Frontend may not connect to backend correctly${NC}"
        echo -e "  ${DIM}Recommended: Create $FRONTEND_DIR/.env.local with:${NC}"
        echo -e "  ${CYAN}NEXT_PUBLIC_API_URL=http://localhost:8000${NC}"
    else
        echo -e "${GREEN}✓ Frontend .env.local exists${NC}"
    fi
}

# Function to check Python virtual environment
check_venv() {
    echo -e "\n${YELLOW}▶ Checking Python Virtual Environment...${NC}"

    # Check if virtual environment exists
    if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
        echo -e "${GREEN}✓ Virtual environment found at .venv${NC}"
        source "$SCRIPT_DIR/.venv/bin/activate"
    elif [ -f "$BACKEND_DIR/.venv/bin/activate" ]; then
        echo -e "${GREEN}✓ Virtual environment found at ele-sdlc-backend/.venv${NC}"
        source "$BACKEND_DIR/.venv/bin/activate"
    else
        echo -e "${RED}✗ Virtual environment not found${NC}"
        echo -e "\n  ${BOLD}Create a Python virtual environment?${NC}"
        echo -e "  ${DIM}Required for running backend and database scripts${NC}"
        echo -e "\n  ${CYAN}[Y]${NC} Yes, create virtual environment ${DIM}(recommended)${NC}"
        echo -e "  ${CYAN}[N]${NC} No, exit"
        echo ""
        read -p "  Your choice [Y/n]: " CREATE_VENV
        CREATE_VENV=${CREATE_VENV:-Y}

        if [[ "$CREATE_VENV" =~ ^[Yy]$ ]]; then
            echo ""
            echo -e "  ${CYAN}Creating virtual environment at .venv...${NC}"
            python3 -m venv "$SCRIPT_DIR/.venv"
            source "$SCRIPT_DIR/.venv/bin/activate"

            echo -e "  ${CYAN}Installing backend dependencies...${NC}"
            cd "$BACKEND_DIR"
            pip install -r requirements.txt
            cd "$SCRIPT_DIR"

            echo -e "  ${GREEN}✓ Virtual environment created and dependencies installed${NC}"
        else
            echo -e "  ${RED}Cannot proceed without virtual environment${NC}"
            return 1
        fi
    fi

    # Verify critical Python packages are installed
    echo -e "  ${CYAN}Verifying Python dependencies...${NC}"
    python -c "import fastapi, langchain, chromadb" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "  ${YELLOW}⚠ Some dependencies missing, installing...${NC}"
        cd "$BACKEND_DIR"
        pip install -r requirements.txt -q
        cd "$SCRIPT_DIR"
    fi
    echo -e "${GREEN}✓ Python dependencies ready${NC}"
}

# Required models for this application
REQUIRED_MODELS=("llama3.1:latest" "all-minilm")

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

    # Pull required models if missing
    if ! echo "$MODELS" | grep -q "all-minilm"; then
        echo -e "  ${YELLOW}Pulling all-minilm model (embeddings)...${NC}"
        ollama pull all-minilm
    fi

    if ! echo "$MODELS" | grep -q "llama3.1"; then
        echo -e "  ${YELLOW}Pulling llama3.1:latest model (generation)...${NC}"
        ollama pull llama3.1:latest
    fi
    echo -e "${GREEN}✓ Required models available${NC}"

    # Clean up unused models (keep only required models)
    cleanup_ollama_models
}

# Function to clean up unused Ollama models
cleanup_ollama_models() {
    echo -e "  ${CYAN}Checking for unused models...${NC}"

    # Get list of all installed models
    INSTALLED_MODELS=$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}')

    if [ -z "$INSTALLED_MODELS" ]; then
        return 0
    fi

    MODELS_TO_REMOVE=""
    while IFS= read -r model; do
        # Skip empty lines
        [ -z "$model" ] && continue

        # Check if this model is required
        IS_REQUIRED=false
        for required in "${REQUIRED_MODELS[@]}"; do
            # Match model name (with or without tag)
            if [[ "$model" == "$required" ]] || [[ "$model" == "${required%:*}"* && "$required" == *":latest" ]]; then
                IS_REQUIRED=true
                break
            fi
            # Also check base name for embedding model
            if [[ "$model" == "all-minilm"* ]]; then
                IS_REQUIRED=true
                break
            fi
            # Check for llama3.1 variants
            if [[ "$model" == "llama3.1"* ]]; then
                IS_REQUIRED=true
                break
            fi
        done

        if [ "$IS_REQUIRED" = false ]; then
            MODELS_TO_REMOVE="$MODELS_TO_REMOVE $model"
        fi
    done <<< "$INSTALLED_MODELS"

    # Remove unused models if any
    if [ -n "$MODELS_TO_REMOVE" ]; then
        echo -e "  ${YELLOW}Found unused models:${NC}$MODELS_TO_REMOVE"
        echo -e "  ${CYAN}Removing unused models to free up disk space...${NC}"
        for model in $MODELS_TO_REMOVE; do
            echo -e "    ${DIM}Removing: $model${NC}"
            ollama rm "$model" 2>/dev/null || true
        done
        echo -e "  ${GREEN}✓ Unused models cleaned up${NC}"
    else
        echo -e "  ${GREEN}✓ No unused models found${NC}"
    fi
}

# Function to generate epic.csv from project folders
generate_epic_csv() {
    echo -e "\n${YELLOW}▶ Generating Epic CSV from Project Folders...${NC}"

    cd "$BACKEND_DIR"

    # Check if projects directory exists and has project folders
    if [ ! -d "data/raw/projects" ]; then
        echo -e "  ${YELLOW}⚠ No data/raw/projects directory found${NC}"
        echo -e "  ${DIM}Cannot generate epic.csv without project folders${NC}"
        cd "$SCRIPT_DIR"
        return 0  # Non-fatal, check_data_files will report the issue
    fi

    # Count project folders (directories only, excluding epic.csv)
    PROJECT_COUNT=$(ls -d data/raw/projects/*/ 2>/dev/null | wc -l | tr -d ' ')
    if [ "$PROJECT_COUNT" -eq 0 ]; then
        echo -e "  ${YELLOW}⚠ No project folders found in data/raw/projects/${NC}"
        echo -e "  ${DIM}Cannot generate epic.csv without project folders${NC}"
        cd "$SCRIPT_DIR"
        return 0
    fi

    # Check if epic.csv exists
    if [ ! -f "data/raw/projects/epic.csv" ]; then
        # No epic.csv - generate it
        echo -e "  ${YELLOW}⚠ epic.csv not found${NC}"
        echo -e "\n  ${BOLD}Generate epic.csv from project folders?${NC}"
        echo -e "  ${DIM}Found ${PROJECT_COUNT} project folders to extract from${NC}"
        echo -e "\n  ${CYAN}[Y]${NC} Yes, generate epic.csv ${DIM}(recommended)${NC}"
        echo -e "  ${CYAN}[N]${NC} No, skip"
        echo ""
        read -p "  Your choice [Y/n]: " GENERATE_CHOICE
        GENERATE_CHOICE=${GENERATE_CHOICE:-Y}

        if [[ "$GENERATE_CHOICE" =~ ^[Yy]$ ]]; then
            echo ""
            echo -e "  ${CYAN}Extracting epic info from project folders...${NC}"
            python scripts/extract_epic_info.py
            if [ $? -eq 0 ]; then
                echo -e "  ${GREEN}✓ epic.csv generated successfully${NC}"
            else
                echo -e "  ${RED}✗ Failed to generate epic.csv${NC}"
                cd "$SCRIPT_DIR"
                return 1
            fi
        else
            echo ""
            echo -e "  ${YELLOW}⚠ Skipping epic.csv generation${NC}"
        fi
    else
        # epic.csv exists - offer to regenerate
        EPIC_COUNT=$(tail -n +2 data/raw/projects/epic.csv 2>/dev/null | wc -l | tr -d ' ')
        echo -e "  ${GREEN}✓ epic.csv exists (${EPIC_COUNT} epics)${NC}"
        echo -e "  ${DIM}Project folders: ${PROJECT_COUNT}${NC}"

        # Check if counts differ (might indicate new projects)
        if [ "$EPIC_COUNT" != "$PROJECT_COUNT" ]; then
            echo -e "  ${YELLOW}⚠ Count mismatch: ${EPIC_COUNT} epics vs ${PROJECT_COUNT} project folders${NC}"
        fi

        echo -e "\n  ${BOLD}Regenerate epic.csv?${NC}"
        echo -e "  ${DIM}Regenerate if you've added new project folders${NC}"
        echo -e "\n  ${CYAN}[S]${NC} Skip, use existing epic.csv ${DIM}(recommended)${NC}"
        echo -e "  ${CYAN}[R]${NC} Regenerate from project folders"
        echo ""
        read -p "  Your choice [S/r]: " REGEN_CHOICE
        REGEN_CHOICE=${REGEN_CHOICE:-S}

        if [[ "$REGEN_CHOICE" =~ ^[Rr]$ ]]; then
            echo ""
            echo -e "  ${CYAN}Regenerating epic.csv from project folders...${NC}"
            python scripts/extract_epic_info.py
            if [ $? -eq 0 ]; then
                echo -e "  ${GREEN}✓ epic.csv regenerated successfully${NC}"
            else
                echo -e "  ${RED}✗ Failed to regenerate epic.csv${NC}"
                cd "$SCRIPT_DIR"
                return 1
            fi
        else
            echo ""
            echo -e "  ${GREEN}✓ Using existing epic.csv${NC}"
        fi
    fi

    cd "$SCRIPT_DIR"
}

# Function to check data files
check_data_files() {
    echo -e "\n${YELLOW}▶ Checking Data Files...${NC}"

    cd "$BACKEND_DIR"

    local has_errors=false

    # Check for epic.csv (required for vectorization)
    if [ ! -f "data/raw/projects/epic.csv" ]; then
        echo -e "  ${RED}✗ data/raw/projects/epic.csv not found${NC}"
        echo -e "    ${DIM}This file is required for vector search initialization${NC}"
        has_errors=true
    else
        echo -e "  ${GREEN}✓ epic.csv found${NC}"
    fi

    # Check projects directory and validate structure
    if [ ! -d "data/raw/projects" ]; then
        echo -e "  ${RED}✗ data/raw/projects/ directory not found${NC}"
        echo -e "    ${DIM}Project documents directory is required${NC}"
        has_errors=true
    elif [ -z "$(ls -A data/raw/projects 2>/dev/null | grep -v 'epic.csv')" ]; then
        echo -e "  ${YELLOW}⚠ No project folders found in data/raw/projects/${NC}"
        echo -e "    ${DIM}Full document loading will not work${NC}"
    else
        # Count project directories (exclude epic.csv)
        PROJECT_COUNT=$(ls -d data/raw/projects/*/ 2>/dev/null | wc -l | tr -d ' ')
        echo -e "  ${GREEN}✓ Project documents directory exists ($PROJECT_COUNT projects)${NC}"

        # Sample check - verify first project has required files
        FIRST_PROJECT=$(ls -d data/raw/projects/*/ 2>/dev/null | head -1)
        if [ -n "$FIRST_PROJECT" ]; then
            local missing_docs=false
            if [ ! -f "${FIRST_PROJECT}tdd.docx" ]; then
                echo -e "    ${YELLOW}⚠ Sample project missing tdd.docx${NC}"
                missing_docs=true
            fi
            if [ ! -f "${FIRST_PROJECT}estimation.xlsx" ]; then
                echo -e "    ${YELLOW}⚠ Sample project missing estimation.xlsx${NC}"
                missing_docs=true
            fi
            if [ ! -f "${FIRST_PROJECT}jira_stories.xlsx" ]; then
                echo -e "    ${YELLOW}⚠ Sample project missing jira_stories.xlsx${NC}"
                missing_docs=true
            fi

            if [ "$missing_docs" = false ]; then
                echo -e "    ${GREEN}✓ Project structure validated${NC}"
            fi
        fi
    fi

    if [ "$has_errors" = true ]; then
        echo -e "\n  ${YELLOW}⚠ Data files missing - vector database may not initialize properly${NC}"
        echo -e "  ${DIM}Expected structure:${NC}"
        echo -e "    ${DIM}data/raw/projects/epic.csv${NC}"
        echo -e "    ${DIM}data/raw/projects/PRJ-XXXXX-name/tdd.docx${NC}"
        echo -e "    ${DIM}data/raw/projects/PRJ-XXXXX-name/estimation.xlsx${NC}"
        echo -e "    ${DIM}data/raw/projects/PRJ-XXXXX-name/jira_stories.xlsx${NC}"
    fi

    cd "$SCRIPT_DIR"
}

# Function to check and initialize ChromaDB
check_chromadb() {
    echo -e "\n${YELLOW}▶ Checking ChromaDB Vector Store...${NC}"

    # Activate virtual environment for database scripts
    if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
        source "$SCRIPT_DIR/.venv/bin/activate"
    elif [ -f "$BACKEND_DIR/.venv/bin/activate" ]; then
        source "$BACKEND_DIR/.venv/bin/activate"
    else
        echo -e "${RED}✗ Virtual environment not found${NC}"
        echo -e "  Create one with: ${CYAN}python -m venv .venv${NC}"
        return 1
    fi

    cd "$BACKEND_DIR"

    # Check if vector database exists
    if [ ! -d "./data/chroma" ] || [ -z "$(ls -A ./data/chroma 2>/dev/null)" ]; then
        # Fresh run - no index exists
        echo -e "  ${YELLOW}⚠ No vector index found${NC}"
        echo -e "\n  ${BOLD}Create a new vector index?${NC}"
        echo -e "  ${DIM}This will index epic metadata from projects/epic.csv${NC}"
        echo -e "\n  ${CYAN}[Y]${NC} Yes, create new index ${DIM}(recommended for first run)${NC}"
        echo -e "  ${CYAN}[N]${NC} No, skip (server will start without vector search)"
        echo ""
        read -p "  Your choice [Y/n]: " CREATE_CHOICE
        CREATE_CHOICE=${CREATE_CHOICE:-Y}  # Default to Yes

        if [[ "$CREATE_CHOICE" =~ ^[Yy]$ ]]; then
            echo ""
            echo -e "  ${CYAN}Creating vector database...${NC}"
            python scripts/init_vector_db.py
            if [ $? -eq 0 ]; then
                echo -e "  ${GREEN}✓ Vector database created successfully${NC}"
            else
                echo -e "  ${RED}✗ Failed to create vector database${NC}"
                return 1
            fi
        else
            echo ""
            echo -e "  ${YELLOW}⚠ Skipping index creation${NC}"
            echo -e "  ${DIM}Vector search may not work correctly${NC}"
        fi
    else
        # Index exists - offer to rebuild
        COLLECTION_COUNT=$(ls -d ./data/chroma/*/ 2>/dev/null | wc -l | tr -d ' ')
        echo -e "  ${GREEN}✓ Existing index found${NC}"
        echo -e "  ${DIM}Location: ./data/chroma${NC}"
        echo -e "  ${DIM}Collections: ${COLLECTION_COUNT} indexed${NC}"
        echo -e "\n  ${BOLD}Rebuild the vector index?${NC}"
        echo -e "  ${DIM}Rebuild if you've updated epic.csv or added new projects${NC}"
        echo -e "\n  ${CYAN}[S]${NC} Skip, use existing index ${DIM}(recommended)${NC}"
        echo -e "  ${CYAN}[R]${NC} Rebuild index ${DIM}(deletes and recreates all collections)${NC}"
        echo ""
        read -p "  Your choice [S/r]: " REBUILD_CHOICE
        REBUILD_CHOICE=${REBUILD_CHOICE:-S}  # Default to Skip

        if [[ "$REBUILD_CHOICE" =~ ^[Rr]$ ]]; then
            echo ""
            echo -e "  ${CYAN}Removing existing ChromaDB data directory...${NC}"
            rm -rf "./data/chroma"
            echo -e "  ${GREEN}✓ ChromaDB data directory cleared${NC}"
            echo ""
            echo -e "  ${CYAN}Rebuilding vector database...${NC}"
            python scripts/init_vector_db.py
            if [ $? -eq 0 ]; then
                echo -e "  ${GREEN}✓ Vector database rebuilt successfully${NC}"
            else
                echo -e "  ${RED}✗ Failed to rebuild vector database${NC}"
                return 1
            fi
        else
            echo ""
            echo -e "  ${GREEN}✓ Using existing index${NC}"
        fi
    fi

    cd "$SCRIPT_DIR"
}

# Function to start main backend
start_backend() {
    echo -e "\n${YELLOW}▶ Starting Main Backend (FastAPI/LangGraph)...${NC}"

    if [ ! -d "$BACKEND_DIR" ]; then
        echo -e "${RED}Error: Backend directory not found at $BACKEND_DIR${NC}"
        return 1
    fi

    # Pre-flight checks (order matters!)
    check_env_files || return 1
    check_venv || return 1
    check_ollama || return 1
    generate_epic_csv || return 1  # Generate epic.csv from project folders
    check_data_files  # Non-blocking - just warns about missing files
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
        # start_pipeline  # Pipeline backend (port 8001) not implemented yet
        start_frontend
        echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}Full stack is now running!${NC}"
        echo -e "  Main Backend:     http://localhost:8000"
        echo -e "  Frontend:         http://localhost:3000"
        echo -e "\n${CYAN}API Documentation:${NC}"
        echo -e "  Main API:     http://localhost:8000/docs"
        echo -e "\n${CYAN}Logs:${NC}"
        echo -e "  Main Backend: tail -f /tmp/sdlc-backend.log"
        echo -e "  Frontend:     tail -f /tmp/sdlc-frontend.log"
        echo -e "\nTo stop: ${YELLOW}./stop.sh${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        ;;
esac
