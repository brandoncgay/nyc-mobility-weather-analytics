#!/bin/bash
# Helper script to start the Analytics Dashboard
# Usage: ./start_analytics_dashboard.sh

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Analytics Dashboard...${NC}"

# Check if port 8501 is in use
if lsof -ti:8501 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port 8501 is already in use${NC}"
    echo -e "Existing process PID: $(lsof -ti:8501)"

    read -p "Kill existing process and restart? (y/n) " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Killing process on port 8501...${NC}"
        kill -9 $(lsof -ti:8501) 2>/dev/null
        sleep 2
        echo -e "${GREEN}✓ Port freed${NC}"
    else
        echo -e "${RED}Cancelled. Try a different port:${NC}"
        echo "  poetry run streamlit run dashboard.py --server.port 8503"
        exit 1
    fi
fi

# Check if database exists
if [ ! -f "data/nyc_mobility.duckdb" ]; then
    echo -e "${RED}❌ Database not found at data/nyc_mobility.duckdb${NC}"
    echo "Run data ingestion first:"
    echo "  poetry run python src/ingestion/run_pipeline.py"
    echo "  cd dbt && poetry run dbt run"
    exit 1
fi

# Start the dashboard
echo -e "${GREEN}Starting dashboard on http://localhost:8501${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

poetry run streamlit run dashboard.py \
    --server.port 8501 \
    --server.headless true

# If we get here, the dashboard was stopped
echo -e "\n${YELLOW}Dashboard stopped${NC}"
