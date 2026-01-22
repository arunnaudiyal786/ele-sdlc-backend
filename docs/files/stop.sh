#!/bin/bash

# SDLC Full Stack Stopper
# Stops both backend and frontend services

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}        SDLC Development Stack Shutdown          ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Function to stop main backend
stop_backend() {
    echo -e "\n${YELLOW}▶ Stopping Main Backend...${NC}"

    # Try PID file first
    if [ -f /tmp/sdlc-backend.pid ]; then
        PID=$(cat /tmp/sdlc-backend.pid)
        if kill -0 $PID 2>/dev/null; then
            kill $PID 2>/dev/null
            echo -e "${GREEN}✓ Main Backend stopped (PID: $PID)${NC}"
        fi
        rm -f /tmp/sdlc-backend.pid
    fi

    # Also kill by process name as fallback
    pkill -f "app.main:app" 2>/dev/null

    # Clean up log file reference
    if [ -f /tmp/sdlc-backend.log ]; then
        echo "  Log preserved at: /tmp/sdlc-backend.log"
    fi
}

# Function to stop pipeline backend
stop_pipeline() {
    echo -e "\n${YELLOW}▶ Stopping Pipeline Backend...${NC}"

    # Try PID file first
    if [ -f /tmp/sdlc-pipeline.pid ]; then
        PID=$(cat /tmp/sdlc-pipeline.pid)
        if kill -0 $PID 2>/dev/null; then
            kill $PID 2>/dev/null
            echo -e "${GREEN}✓ Pipeline Backend stopped (PID: $PID)${NC}"
        fi
        rm -f /tmp/sdlc-pipeline.pid
    fi

    # Also kill by process name as fallback
    pkill -f "pipeline.main:app" 2>/dev/null

    # Clean up log file reference
    if [ -f /tmp/sdlc-pipeline.log ]; then
        echo "  Log preserved at: /tmp/sdlc-pipeline.log"
    fi
}

# Function to stop frontend
stop_frontend() {
    echo -e "\n${YELLOW}▶ Stopping Frontend...${NC}"

    # Try PID file first
    if [ -f /tmp/sdlc-frontend.pid ]; then
        PID=$(cat /tmp/sdlc-frontend.pid)
        if kill -0 $PID 2>/dev/null; then
            kill $PID 2>/dev/null
            echo -e "${GREEN}✓ Frontend stopped (PID: $PID)${NC}"
        fi
        rm -f /tmp/sdlc-frontend.pid
    fi

    # Also kill Next.js dev server processes as fallback
    pkill -f "next dev" 2>/dev/null
    pkill -f "next-server" 2>/dev/null

    # Clean up log file reference
    if [ -f /tmp/sdlc-frontend.log ]; then
        echo "  Log preserved at: /tmp/sdlc-frontend.log"
    fi
}

# Parse arguments
case "${1:-all}" in
    backend)
        stop_backend
        ;;
    pipeline)
        stop_pipeline
        ;;
    frontend)
        stop_frontend
        ;;
    all|*)
        stop_backend
        stop_pipeline
        stop_frontend
        echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}All services stopped.${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        ;;
esac
