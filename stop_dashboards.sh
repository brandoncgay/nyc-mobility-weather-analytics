#!/bin/bash
# Helper script to stop all running dashboards
# Usage: ./stop_dashboards.sh

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛑 Stopping all dashboards...${NC}"

# Function to stop dashboard on a port
stop_port() {
    local port=$1
    local name=$2

    if lsof -ti:$port > /dev/null 2>&1; then
        echo -e "Stopping ${name} on port ${port}..."
        kill -9 $(lsof -ti:$port) 2>/dev/null
        sleep 1

        if lsof -ti:$port > /dev/null 2>&1; then
            echo -e "${RED}✗ Failed to stop port ${port}${NC}"
            return 1
        else
            echo -e "${GREEN}✓ Stopped ${name}${NC}"
            return 0
        fi
    else
        echo -e "${YELLOW}ℹ ${name} not running on port ${port}${NC}"
        return 0
    fi
}

# Stop both dashboards
stopped=0

stop_port 8501 "Analytics Dashboard"
stopped=$((stopped + $?))

stop_port 8502 "Data Quality Dashboard"
stopped=$((stopped + $?))

# Also check for any other Streamlit processes
streamlit_pids=$(ps aux | grep '[s]treamlit run dashboard' | awk '{print $2}')
if [ -n "$streamlit_pids" ]; then
    echo -e "${YELLOW}Found additional Streamlit processes:${NC}"
    echo "$streamlit_pids"
    read -p "Kill these processes too? (y/n) " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "$streamlit_pids" | xargs kill -9 2>/dev/null
        echo -e "${GREEN}✓ Stopped additional processes${NC}"
    fi
fi

echo ""
if [ $stopped -eq 0 ]; then
    echo -e "${GREEN}✅ All dashboards stopped${NC}"
else
    echo -e "${YELLOW}⚠️  Some dashboards may still be running${NC}"
    echo "Check manually with: lsof -ti:8501,8502"
fi
