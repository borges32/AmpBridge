#!/bin/bash
# Script de teste completo para OpAMP Backend API

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  OpAMP Backend API - Test Suite       ║${NC}"
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo ""

# Configuration
API_BASE="http://localhost:8000"
API_V1="$API_BASE/api/v1"

# Check if API is running
echo -e "${YELLOW}[1/10] Checking API health...${NC}"
if curl -s "$API_BASE/health" > /dev/null; then
    echo -e "${GREEN}✓ API is running${NC}"
else
    echo -e "${RED}✗ API is not running. Please start with: docker compose up -d${NC}"
    exit 1
fi
echo ""

# Test 1: Register user
echo -e "${YELLOW}[2/10] Registering test user...${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "$API_V1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "login": "testuser",
    "password": "testpass123"
  }')

if echo "$REGISTER_RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    USER_ID=$(echo "$REGISTER_RESPONSE" | jq -r '.id')
    echo -e "${GREEN}✓ User registered successfully (ID: $USER_ID)${NC}"
else
    # User might already exist
    echo -e "${YELLOW}⚠ User might already exist (continuing...)${NC}"
fi
echo ""

# Test 2: Login
echo -e "${YELLOW}[3/10] Logging in...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_V1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "login": "testuser",
    "password": "testpass123"
  }')

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    echo -e "${GREEN}✓ Login successful${NC}"
    echo "Token: ${TOKEN:0:20}..."
else
    echo -e "${RED}✗ Login failed${NC}"
    echo "$LOGIN_RESPONSE"
    exit 1
fi
echo ""

# Test 3: Get current user
echo -e "${YELLOW}[4/10] Getting current user info...${NC}"
ME_RESPONSE=$(curl -s "$API_V1/auth/me" \
  -H "Authorization: Bearer $TOKEN")

if echo "$ME_RESPONSE" | jq -e '.login' > /dev/null 2>&1; then
    USER_LOGIN=$(echo "$ME_RESPONSE" | jq -r '.login')
    echo -e "${GREEN}✓ Current user: $USER_LOGIN${NC}"
else
    echo -e "${RED}✗ Failed to get user info${NC}"
    exit 1
fi
echo ""

# Test 4: Trigger manual sync
echo -e "${YELLOW}[5/10] Triggering OpAMP sync...${NC}"
SYNC_RESPONSE=$(curl -s -X POST "$API_V1/opamp/sync" \
  -H "Authorization: Bearer $TOKEN")

if echo "$SYNC_RESPONSE" | jq -e '.success' > /dev/null 2>&1; then
    AGENTS_PROCESSED=$(echo "$SYNC_RESPONSE" | jq -r '.agents_processed')
    AGENTS_UPDATED=$(echo "$SYNC_RESPONSE" | jq -r '.agents_updated')
    CONFIGS_VERSIONED=$(echo "$SYNC_RESPONSE" | jq -r '.configs_versioned')
    echo -e "${GREEN}✓ Sync completed${NC}"
    echo "  - Agents processed: $AGENTS_PROCESSED"
    echo "  - Agents updated: $AGENTS_UPDATED"
    echo "  - Configs versioned: $CONFIGS_VERSIONED"
else
    echo -e "${YELLOW}⚠ Sync might have failed (check logs)${NC}"
fi
echo ""

# Test 5: List agents
echo -e "${YELLOW}[6/10] Listing agents...${NC}"
AGENTS_RESPONSE=$(curl -s "$API_V1/agents?page=1&page_size=10")

if echo "$AGENTS_RESPONSE" | jq -e '.agents' > /dev/null 2>&1; then
    TOTAL_AGENTS=$(echo "$AGENTS_RESPONSE" | jq -r '.total')
    echo -e "${GREEN}✓ Agents listed successfully${NC}"
    echo "  - Total agents: $TOTAL_AGENTS"
    
    # Get first agent ID if available
    FIRST_AGENT_ID=$(echo "$AGENTS_RESPONSE" | jq -r '.agents[0].instance_id // empty')
    
    if [ -n "$FIRST_AGENT_ID" ]; then
        echo "  - First agent: $FIRST_AGENT_ID"
    fi
else
    echo -e "${RED}✗ Failed to list agents${NC}"
    exit 1
fi
echo ""

# Test 6: Get specific agent (if exists)
if [ -n "$FIRST_AGENT_ID" ]; then
    echo -e "${YELLOW}[7/10] Getting agent details...${NC}"
    AGENT_RESPONSE=$(curl -s "$API_V1/agents/$FIRST_AGENT_ID")
    
    if echo "$AGENT_RESPONSE" | jq -e '.instance_id' > /dev/null 2>&1; then
        HOST_NAME=$(echo "$AGENT_RESPONSE" | jq -r '.host_name // "N/A"')
        HEALTHY=$(echo "$AGENT_RESPONSE" | jq -r '.healthy')
        STATUS_SYNC=$(echo "$AGENT_RESPONSE" | jq -r '.status_sync')
        echo -e "${GREEN}✓ Agent details retrieved${NC}"
        echo "  - Host: $HOST_NAME"
        echo "  - Healthy: $HEALTHY"
        echo "  - Status: $STATUS_SYNC"
    else
        echo -e "${RED}✗ Failed to get agent details${NC}"
    fi
    echo ""
else
    echo -e "${YELLOW}[7/10] Skipping agent details (no agents found)${NC}"
    echo ""
fi

# Test 7: Get agent health history (if agent exists)
if [ -n "$FIRST_AGENT_ID" ]; then
    echo -e "${YELLOW}[8/10] Getting agent health history...${NC}"
    HEALTH_RESPONSE=$(curl -s "$API_V1/agents/$FIRST_AGENT_ID/health?limit=5")
    
    if echo "$HEALTH_RESPONSE" | jq -e '.[0]' > /dev/null 2>&1; then
        HEALTH_COUNT=$(echo "$HEALTH_RESPONSE" | jq '. | length')
        echo -e "${GREEN}✓ Health history retrieved${NC}"
        echo "  - Records: $HEALTH_COUNT"
    else
        echo -e "${YELLOW}⚠ No health records found${NC}"
    fi
    echo ""
else
    echo -e "${YELLOW}[8/10] Skipping health history (no agents found)${NC}"
    echo ""
fi

# Test 8: Get agent config history (if agent exists)
if [ -n "$FIRST_AGENT_ID" ]; then
    echo -e "${YELLOW}[9/10] Getting agent config history...${NC}"
    CONFIG_RESPONSE=$(curl -s "$API_V1/agents/$FIRST_AGENT_ID/configs?limit=5")
    
    if echo "$CONFIG_RESPONSE" | jq -e '.[0]' > /dev/null 2>&1; then
        CONFIG_COUNT=$(echo "$CONFIG_RESPONSE" | jq '. | length')
        LATEST_VERSION=$(echo "$CONFIG_RESPONSE" | jq -r '.[0].version')
        echo -e "${GREEN}✓ Config history retrieved${NC}"
        echo "  - Versions: $CONFIG_COUNT"
        echo "  - Latest version: $LATEST_VERSION"
    else
        echo -e "${YELLOW}⚠ No config versions found${NC}"
    fi
    echo ""
else
    echo -e "${YELLOW}[9/10] Skipping config history (no agents found)${NC}"
    echo ""
fi

# Test 9: Export agents to CSV
echo -e "${YELLOW}[10/10] Exporting agents to CSV...${NC}"
CSV_FILE="/tmp/agents_export_test.csv"
HTTP_CODE=$(curl -s -o "$CSV_FILE" -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  "$API_V1/agents/csv")

if [ "$HTTP_CODE" = "200" ] && [ -f "$CSV_FILE" ]; then
    LINE_COUNT=$(wc -l < "$CSV_FILE")
    echo -e "${GREEN}✓ CSV export successful${NC}"
    echo "  - File: $CSV_FILE"
    echo "  - Lines: $LINE_COUNT"
    echo "  - Preview:"
    head -3 "$CSV_FILE" | sed 's/^/    /'
else
    echo -e "${RED}✗ CSV export failed (HTTP $HTTP_CODE)${NC}"
fi
echo ""

# Summary
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Test Suite Completed!                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo "  1. Check API documentation: $API_BASE/docs"
echo "  2. Monitor sync logs: docker logs -f opamp-backend"
echo "  3. Access database: docker exec -it opamp-postgres psql -U opamp -d opamp_db"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
