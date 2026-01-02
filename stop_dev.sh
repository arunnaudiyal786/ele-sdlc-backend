#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Symbols
CHECK="${GREEN}✓${NC}"
CROSS="${RED}✗${NC}"
ARROW="${CYAN}➜${NC}"
WARN="${YELLOW}⚠${NC}"

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}  ${BOLD}AI Impact Assessment - Shutdown${NC}                           ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Track what was stopped
STOPPED_SOMETHING=false

# ─────────────────────────────────────────────────────────────
# Step 1: Stop API Server (uvicorn)
# ─────────────────────────────────────────────────────────────
echo -e "${ARROW} ${BOLD}[1/3] Stopping API Server...${NC}"

if pgrep -f "uvicorn app.main:app" > /dev/null 2>&1; then
    pkill -f "uvicorn app.main:app"
    sleep 1
    if ! pgrep -f "uvicorn app.main:app" > /dev/null 2>&1; then
        echo -e "      ${CHECK} API Server (uvicorn) stopped"
        STOPPED_SOMETHING=true
    else
        echo -e "      ${CROSS} Failed to stop API Server"
    fi
else
    echo -e "      ${WARN} API Server was not running"
fi

# Also check for api_server.py (legacy)
if pgrep -f "api_server.py" > /dev/null 2>&1; then
    pkill -f "api_server.py"
    echo -e "      ${CHECK} Legacy API Server stopped"
    STOPPED_SOMETHING=true
fi

# ─────────────────────────────────────────────────────────────
# Step 2: Stop Ollama (optional - ask user)
# ─────────────────────────────────────────────────────────────
echo ""
echo -e "${ARROW} ${BOLD}[2/3] Checking Ollama...${NC}"

if pgrep -f "ollama serve" > /dev/null 2>&1; then
    echo -e "      ${WARN} Ollama is running"
    echo ""
    echo -e "      ${YELLOW}Stop Ollama server? (y/N):${NC} "
    read -r -t 10 STOP_OLLAMA

    if [[ "$STOP_OLLAMA" =~ ^[Yy]$ ]]; then
        pkill -f "ollama serve"
        sleep 1
        if ! pgrep -f "ollama serve" > /dev/null 2>&1; then
            echo -e "      ${CHECK} Ollama server stopped"
            STOPPED_SOMETHING=true
        else
            echo -e "      ${CROSS} Failed to stop Ollama"
        fi
    else
        echo -e "      ${ARROW} Ollama left running (shared resource)"
    fi
else
    echo -e "      ${WARN} Ollama was not running"
fi

# ─────────────────────────────────────────────────────────────
# Step 3: Cleanup and Summary
# ─────────────────────────────────────────────────────────────
echo ""
echo -e "${ARROW} ${BOLD}[3/3] Cleanup Complete${NC}"
echo ""

# Summary box
echo -e "${BLUE}┌────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│${NC}  ${BOLD}Service Status Summary${NC}                                     ${BLUE}│${NC}"
echo -e "${BLUE}├────────────────────────────────────────────────────────────┤${NC}"

# API Server status
if ! pgrep -f "uvicorn app.main:app" > /dev/null 2>&1; then
    echo -e "${BLUE}│${NC}    API Server     ${CHECK} Stopped                               ${BLUE}│${NC}"
else
    echo -e "${BLUE}│${NC}    API Server     ${CROSS} Still running                         ${BLUE}│${NC}"
fi

# Ollama status
if pgrep -f "ollama serve" > /dev/null 2>&1; then
    echo -e "${BLUE}│${NC}    Ollama         ${GREEN}●${NC} Running (available for other apps)    ${BLUE}│${NC}"
else
    echo -e "${BLUE}│${NC}    Ollama         ${RED}●${NC} Stopped                              ${BLUE}│${NC}"
fi

# ChromaDB status (file-based, always available)
echo -e "${BLUE}│${NC}    ChromaDB       ${GREEN}●${NC} Persisted in ./data/chroma           ${BLUE}│${NC}"

echo -e "${BLUE}└────────────────────────────────────────────────────────────┘${NC}"
echo ""

if [ "$STOPPED_SOMETHING" = true ]; then
    echo -e "${GREEN}${BOLD}Shutdown complete!${NC}"
else
    echo -e "${YELLOW}Nothing was running.${NC}"
fi
echo ""
