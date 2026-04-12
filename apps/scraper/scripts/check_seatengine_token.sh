#!/usr/bin/env bash
# check_seatengine_token.sh
#
# Verifies that the SEATENGINE_AUTH_TOKEN in .env is still accepted by the
# SeatEngine v1 API. Exits 0 if valid, 1 if invalid or missing.
#
# Usage:
#   bash check_seatengine_token.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

# Load token from .env
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: .env not found at $ENV_FILE" >&2
  exit 1
fi

TOKEN=$(grep "^SEATENGINE_AUTH_TOKEN=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 | tr -d '[:space:]')

if [[ -z "$TOKEN" ]]; then
  echo "Error: SEATENGINE_AUTH_TOKEN not set in $ENV_FILE" >&2
  exit 1
fi

echo "Token: $TOKEN"

# Verify against venue 21 (Vermont Comedy Club — reliably has shows)
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "https://services.seatengine.com/api/v1/venues/21/shows" \
  -H "x-auth-token: $TOKEN" \
  --max-time 10)

if [[ "$HTTP_STATUS" == "200" ]]; then
  echo "Status: VALID (HTTP 200)"
  exit 0
elif [[ "$HTTP_STATUS" == "401" ]]; then
  echo "Status: EXPIRED (HTTP 401)" >&2
  exit 1
else
  echo "Status: UNKNOWN (HTTP $HTTP_STATUS)" >&2
  exit 1
fi
