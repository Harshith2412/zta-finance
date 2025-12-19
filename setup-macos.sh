#!/bin/bash

# ZTA-Finance Setup Script for macOS
# This script handles Python 3.13 compatibility and Docker installation

set -e

echo "=============================================="
echo "ZTA-Finance macOS Setup"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${YELLOW}Detected Python version: $PYTHON_VERSION${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed${NC}"
    echo ""
    echo "Please install Docker Desktop for Mac from:"
    echo "https://www.docker.com/products/docker-desktop"
    echo ""
    echo "After installation, run this script again."
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Docker is not running${NC}"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed and running${NC}"

# Check for docker compose (v2 syntax)
if docker compose version &> /dev/null; then
    echo -e "${GREEN}✓ Docker Compose v2 detected${NC}"
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✓ Docker Compose v1 detected${NC}"
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}Docker Compose not found${NC}"
    echo "It should come with Docker Desktop. Please reinstall Docker Desktop."
    exit 1
fi

echo ""
echo "=============================================="
echo "Step 1: Generate Security Keys"
echo "=============================================="

# Check if .env already exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file already exists${NC}"
    read -p "Do you want to regenerate keys? (y/N): " -n 1 -r
    echo
    if [[ ! $REPL =~ ^[Yy]$ ]]; then
        echo "Using existing .env file"
    else
        python3 scripts/generate_keys.py
    fi
else
    python3 scripts/generate_keys.py
fi

echo ""
echo "=============================================="
echo "Step 2: Starting Services with Docker"
echo "=============================================="

# Start services
$DOCKER_COMPOSE up -d

echo ""
echo "Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "=============================================="
echo "Service Status"
echo "=============================================="
$DOCKER_COMPOSE ps

echo ""
echo "=============================================="
echo "Step 3: Verify API Health"
echo "=============================================="

# Wait a bit more for API to fully start
sleep 5

# Check API health
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo -e "${GREEN}✓ API is healthy and running${NC}"
else
    echo -e "${YELLOW}Warning: API might still be starting. Check logs with:${NC}"
    echo "$DOCKER_COMPOSE logs -f zta-api"
fi

echo ""
echo "=============================================="
echo "✓ Setup Complete!"
echo "=============================================="
echo ""
echo "Your ZTA-Finance system is running!"
echo ""
echo "Access points:"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - MySQL: localhost:3306"
echo "  - Redis: localhost:6379"
echo ""
echo "Useful commands:"
echo "  View logs:     $DOCKER_COMPOSE logs -f"
echo "  Stop services: $DOCKER_COMPOSE stop"
echo "  Restart:       $DOCKER_COMPOSE restart"
echo ""
echo "See COMMANDS.md for more information"
echo ""