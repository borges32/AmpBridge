#!/bin/bash

# OpAMP Stack - Quick Setup Script
# This script helps you get started with the OpAMP platform quickly

set -e

echo "========================================="
echo "  OpAMP Platform - Quick Setup"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed${NC}"
echo ""

# Navigate to opamp-stack directory
cd "$(dirname "$0")/opamp-stack" || exit

echo "📦 Setting up backend environment..."

# Create backend .env if it doesn't exist
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo -e "${GREEN}✓ Created backend/.env${NC}"
else
    echo -e "${YELLOW}! backend/.env already exists, skipping${NC}"
fi

echo ""
echo "📦 Setting up frontend environment..."

# Create frontend .env if it doesn't exist
if [ ! -f frontend/.env ]; then
    cp frontend/.env.example frontend/.env
    echo -e "${GREEN}✓ Created frontend/.env${NC}"
else
    echo -e "${YELLOW}! frontend/.env already exists, skipping${NC}"
fi

echo ""
echo "🐳 Starting Docker containers..."
echo "This may take a few minutes on first run..."
echo ""

# Start docker-compose
if docker compose version &> /dev/null; then
    docker compose up -d --build
else
    docker-compose up -d --build
fi

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  ✓ Setup Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "🌐 Access URLs:"
echo "  • Frontend Dashboard: http://localhost:3000"
echo "  • Backend API:        http://localhost:8000"
echo "  • API Docs:           http://localhost:8000/docs"
echo "  • OpAMP Server:       http://localhost:4321"
echo ""
echo "🔐 Default Login Credentials:"
echo "  • Username: admin"
echo "  • Password: admin"
echo ""
echo "📝 Useful Commands:"
echo "  • View logs:    docker compose logs -f"
echo "  • Stop all:     docker compose down"
echo "  • Restart:      docker compose restart"
echo ""
echo -e "${YELLOW}⏳ Containers are starting up...${NC}"
echo -e "${YELLOW}   Wait 10-20 seconds for all services to be ready${NC}"
echo ""
echo "Happy managing! 🚀"
