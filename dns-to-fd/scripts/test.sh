#!/usr/bin/env bash

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
PDF_FILE="${PDF_FILE:-data/test.pdf}"

az login --tenant "c04e3789-3880-4e6e-a01c-28b66b6c4948"
TOKEN=$(echo $(az account get-access-token --scope api://d6e0c517-7a34-4b6c-9688-48557307eb1a/access_as_user  --query accessToken) | tr -d '"')

USER_RESPONSE=$(curl -sS -X POST "$BASE_URL/api/v1/users" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"endpoint-test-user","role": ["App.User", "App.Admin"]}')
echo "$USER_RESPONSE"
USER_ID=$(printf '%s' "$USER_RESPONSE" | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')

curl -sS -X GET "$BASE_URL/api/v1/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN"
echo

DOCUMENT_RESPONSE=$(curl -sS -X POST "$BASE_URL/api/v1/users/$USER_ID/documents/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$PDF_FILE;type=application/pdf")
echo "$DOCUMENT_RESPONSE"
DOCUMENT_ID=$(printf '%s' "$DOCUMENT_RESPONSE" | python3 -c 'import json, sys; print(json.load(sys.stdin)["document_id"])')

curl -sS -X GET "$BASE_URL/api/v1/users/$USER_ID/documents/$DOCUMENT_ID" \
  -H "Authorization: Bearer $TOKEN"
echo

#curl -sS -X DELETE "$BASE_URL/api/v1/users/$USER_ID/documents/$DOCUMENT_ID" \
#  -H "Authorization: Bearer $TOKEN"
#echo

curl -sS -X DELETE "$BASE_URL/api/v1/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN"
echo
