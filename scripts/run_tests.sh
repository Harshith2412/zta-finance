#!/bin/bash

# ZTA-Finance Test Runner
# Runs all tests with coverage reporting

set -e

echo "=============================================="
echo "ZTA-Finance Test Suite"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Virtual environment not activated${NC}"
    echo "Consider activating venv: source venv/bin/activate"
    echo ""
fi

# Check if pytest is installed
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${RED}Error: pytest not installed${NC}"
    echo "Install with: pip install -r requirements.txt"
    exit 1
fi

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run tests with different options based on arguments
if [ "$1" = "coverage" ]; then
    echo "Running tests with coverage..."
    pytest tests/ \
        --cov=src \
        --cov-report=html \
        --cov-report=term-missing \
        --cov-report=xml \
        -v \
        --tb=short
    
    echo ""
    echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
    
elif [ "$1" = "unit" ]; then
    echo "Running unit tests only..."
    pytest tests/ \
        -v \
        --tb=short \
        -m "not integration"
    
elif [ "$1" = "integration" ]; then
    echo "Running integration tests only..."
    pytest tests/ \
        -v \
        --tb=short \
        -m integration
    
elif [ "$1" = "watch" ]; then
    echo "Running tests in watch mode..."
    pytest tests/ \
        -v \
        --tb=short \
        -f
    
elif [ "$1" = "verbose" ]; then
    echo "Running tests in verbose mode..."
    pytest tests/ \
        -vv \
        --tb=long \
        -s
    
elif [ "$1" = "fast" ]; then
    echo "Running tests in fast mode (no coverage)..."
    pytest tests/ \
        -v \
        --tb=short \
        -x
    
else
    echo "Running all tests..."
    pytest tests/ \
        -v \
        --tb=short
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi