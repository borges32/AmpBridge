#!/bin/bash

# Script to test the single agent sync endpoint
# Usage: ./test_sync_single_agent.sh [instance_id]

set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# API configuration
API_BASE="http://localhost:8000"
API_V1="$API_BASE/api/v1"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Single Agent Sync Endpoint Test${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Test 1: Login to get token
echo -e "${YELLOW}[1/4] Logging in...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_V1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "login": "admin",
    "password": "admin123"
  }')

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Failed to login${NC}"
    echo "$LOGIN_RESPONSE" | jq .
    exit 1
fi

echo -e "${GREEN}✓ Login successful${NC}"
echo ""

# Test 2: Get list of agents to find a valid instance_id
echo -e "${YELLOW}[2/4] Fetching agents list...${NC}"
AGENTS_RESPONSE=$(curl -s "$API_V1/agents?page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN")

TOTAL_AGENTS=$(echo "$AGENTS_RESPONSE" | jq -r '.total')

if [ "$TOTAL_AGENTS" == "0" ]; then
    echo -e "${YELLOW}⚠ No agents found. Running full sync first...${NC}"
    curl -s -X POST "$API_V1/opamp/sync" \
      -H "Authorization: Bearer $TOKEN" > /dev/null
    
    # Fetch agents again
    AGENTS_RESPONSE=$(curl -s "$API_V1/agents?page=1&page_size=10" \
      -H "Authorization: Bearer $TOKEN")
    TOTAL_AGENTS=$(echo "$AGENTS_RESPONSE" | jq -r '.total')
fi

echo -e "${GREEN}✓ Found $TOTAL_AGENTS agent(s)${NC}"

# Get the first agent's instance_id or use the one provided as argument
if [ -n "$1" ]; then
    INSTANCE_ID="$1"
    echo -e "${GREEN}✓ Using provided instance_id: $INSTANCE_ID${NC}"
else
    INSTANCE_ID=$(echo "$AGENTS_RESPONSE" | jq -r '.agents[0].instance_id')
    if [ "$INSTANCE_ID" == "null" ] || [ -z "$INSTANCE_ID" ]; then
        echo -e "${RED}✗ No agents available to sync${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Using first agent's instance_id: $INSTANCE_ID${NC}"
fi
echo ""

# Test 3: Sync the specific agent
echo -e "${YELLOW}[3/4] Syncing agent $INSTANCE_ID...${NC}"
SYNC_RESPONSE=$(curl -s -X POST "$API_V1/opamp/sync/$INSTANCE_ID" \
  -H "Authorization: Bearer $TOKEN")

SUCCESS=$(echo "$SYNC_RESPONSE" | jq -r '.success')

if [ "$SUCCESS" == "true" ]; then
    MESSAGE=$(echo "$SYNC_RESPONSE" | jq -r '.message')
    UPDATED=$(echo "$SYNC_RESPONSE" | jq -r '.updated')
    CONFIG_VERSIONED=$(echo "$SYNC_RESPONSE" | jq -r '.config_versioned')
    
    echo -e "${GREEN}✓ Sync successful${NC}"
    echo "  Message: $MESSAGE"
    echo "  Updated: $UPDATED"
    echo "  Config Versioned: $CONFIG_VERSIONED"
else
    echo -e "${RED}✗ Sync failed${NC}"
    echo "$SYNC_RESPONSE" | jq .
    exit 1
fi
echo ""

# Test 4: Test with non-existent agent (should return 404)
echo -e "${YELLOW}[4/4] Testing with non-existent agent...${NC}"
FAKE_ID="non-existent-agent-id-12345"
ERROR_RESPONSE=$(curl -s -X POST "$API_V1/opamp/sync/$FAKE_ID" \
  -H "Authorization: Bearer $TOKEN" -w "\n%{http_code}")

HTTP_CODE=$(echo "$ERROR_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$ERROR_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "404" ]; then
    echo -e "${GREEN}✓ Correctly returned 404 for non-existent agent${NC}"
    DETAIL=$(echo "$RESPONSE_BODY" | jq -r '.detail')
    echo "  Error: $DETAIL"
else
    echo -e "${RED}✗ Expected 404, got $HTTP_CODE${NC}"
    echo "$RESPONSE_BODY" | jq .
fi
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All tests completed!${NC}"
echo -e "${GREEN}========================================${NC}"
