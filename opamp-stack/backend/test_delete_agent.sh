#!/bin/bash

# Script to test the DELETE agent endpoint
# Usage: ./test_delete_agent.sh <instance_id>

BASE_URL="http://localhost:8000/api/v1"
INSTANCE_ID="${1:-test-agent-instance-id}"

echo "==================================="
echo "Testing DELETE Agent Endpoint"
echo "==================================="
echo ""

# Step 1: Login to get token
echo "1. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123")

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to login. Response:"
  echo $LOGIN_RESPONSE
  exit 1
fi

echo "✅ Login successful"
echo ""

# Step 2: Check if agent exists
echo "2. Checking if agent exists..."
AGENT_RESPONSE=$(curl -s -X GET "${BASE_URL}/agents/${INSTANCE_ID}" \
  -H "Authorization: Bearer ${TOKEN}")

if echo $AGENT_RESPONSE | grep -q "not found"; then
  echo "⚠️  Agent '${INSTANCE_ID}' not found"
  echo ""
  echo "Available agents:"
  curl -s -X GET "${BASE_URL}/agents?page=1&page_size=10" \
    -H "Authorization: Bearer ${TOKEN}" | jq -r '.agents[] | .instance_id'
  exit 1
fi

echo "✅ Agent exists:"
echo $AGENT_RESPONSE | jq '.'
echo ""

# Step 3: Get agent statistics before deletion
echo "3. Getting statistics before deletion..."
STATS_BEFORE=$(curl -s -X GET "${BASE_URL}/agents/stats" \
  -H "Authorization: Bearer ${TOKEN}")
echo "Stats before:"
echo $STATS_BEFORE | jq '.'
echo ""

# Step 4: Delete the agent
echo "4. Deleting agent '${INSTANCE_ID}'..."
DELETE_RESPONSE=$(curl -s -X DELETE "${BASE_URL}/agents/${INSTANCE_ID}" \
  -H "Authorization: Bearer ${TOKEN}")

echo "Delete response:"
echo $DELETE_RESPONSE | jq '.'
echo ""

if echo $DELETE_RESPONSE | grep -q '"success":true'; then
  echo "✅ Agent deleted successfully!"
else
  echo "❌ Failed to delete agent"
  exit 1
fi

# Step 5: Verify agent is gone
echo "5. Verifying agent is deleted..."
VERIFY_RESPONSE=$(curl -s -X GET "${BASE_URL}/agents/${INSTANCE_ID}" \
  -H "Authorization: Bearer ${TOKEN}")

if echo $VERIFY_RESPONSE | grep -q "not found"; then
  echo "✅ Agent successfully removed from database"
else
  echo "❌ Agent still exists!"
  echo $VERIFY_RESPONSE | jq '.'
  exit 1
fi

# Step 6: Get agent statistics after deletion
echo ""
echo "6. Getting statistics after deletion..."
STATS_AFTER=$(curl -s -X GET "${BASE_URL}/agents/stats" \
  -H "Authorization: Bearer ${TOKEN}")
echo "Stats after:"
echo $STATS_AFTER | jq '.'
echo ""

echo "==================================="
echo "✅ All tests passed!"
echo "==================================="
