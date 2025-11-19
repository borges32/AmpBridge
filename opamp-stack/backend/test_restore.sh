#!/bin/bash

# Test the restore endpoint
# First login to get a token

echo "Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123")

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "Failed to login"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "Token obtained: ${TOKEN:0:20}..."

# Get agent config history
echo ""
echo "Getting config history..."
INSTANCE_ID="019fa7534-f534-70ab-bbbc-115e20231708"
curl -s "http://localhost:8000/api/v1/agents/$INSTANCE_ID/configs" | jq '.[] | {version: .version, source: .source, created_at: .created_at}'

# Test restore endpoint
echo ""
echo "Testing restore endpoint for version 1..."
RESTORE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/agents/$INSTANCE_ID/config/restore?version=1" \
  -H "Authorization: Bearer $TOKEN")

echo "Restore response:"
echo $RESTORE_RESPONSE | jq '.'
