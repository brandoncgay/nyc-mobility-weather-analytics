#!/bin/bash

# NYC Mobility & Weather Analytics - Environment Setup Script
# This script sets up the development environment

set -e  # Exit on error

echo "🚀 NYC Mobility & Weather Analytics - Setup Script"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}❌ Poetry is not installed${NC}"
    echo "Please install Poetry first: https://python-poetry.org/docs/#installation"
    exit 1
fi

echo -e "${GREEN}✓ Poetry found${NC}"

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}❌ Python 3.11 or higher is required${NC}"
    echo "Current version: $PYTHON_VERSION"
    exit 1
fi

echo -e "${GREEN}✓ Python version OK ($PYTHON_VERSION)${NC}"
echo ""

# Step 1: Copy environment template
echo "📋 Step 1: Setting up environment variables..."
if [ ! -f .env ]; then
    cp .env.template .env
    echo -e "${GREEN}✓ Created .env file from template${NC}"
    echo -e "${YELLOW}⚠️  Remember to add your API keys to .env${NC}"
else
    echo -e "${YELLOW}⚠️  .env file already exists, skipping${NC}"
fi
echo ""

# Step 2: Install dependencies
echo "📦 Step 2: Installing Python dependencies..."
poetry install
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Step 3: Set up pre-commit hooks
echo "🔧 Step 3: Setting up pre-commit hooks..."
poetry run pre-commit install
echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"
echo ""

# Step 4: Create data directories
echo "📁 Step 4: Creating data directories..."
mkdir -p data/{raw,bronze,silver,gold}
mkdir -p notebooks
echo -e "${GREEN}✓ Data directories created${NC}"
echo ""

# Step 5: Initialize DuckDB database
echo "🦆 Step 5: Initializing DuckDB database..."
poetry run python -c "import duckdb; conn = duckdb.connect('data/nyc_mobility.duckdb'); conn.close()"
echo -e "${GREEN}✓ DuckDB database initialized${NC}"
echo ""

# Step 6: Run tests
echo "🧪 Step 6: Running tests to verify setup..."
if poetry run pytest; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${RED}❌ Some tests failed${NC}"
    echo "Please check the errors above"
fi
echo ""

# Summary
echo "=================================================="
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Review and update .env with absolute paths (especially DUCKDB_PATH)"
echo "2. Run 'poetry shell' to activate the virtual environment"
echo "3. Start with MVP 1: Data ingestion"
echo ""
echo "Useful commands:"
echo "  poetry shell              - Activate virtual environment"
echo "  poetry run pytest         - Run tests"
echo "  poetry run ruff check .   - Lint code"
echo "  poetry run jupyter notebook - Start Jupyter"
echo ""
echo "For more information, see docs/setup.md"
echo "=================================================="
