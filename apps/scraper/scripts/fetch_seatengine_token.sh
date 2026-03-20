#!/usr/bin/env bash
# fetch_seatengine_token.sh
#
# Extracts SEATENGINE_AUTH_TOKEN from SeatEngine's public React cart bundle
# and writes it to apps/scraper/.env (and optionally GitHub secrets).
#
# Usage:
#   bash fetch_seatengine_token.sh [--gh-secret] [--venue-url <url>]
#
# Options:
#   --gh-secret          Also set the token in GitHub Actions secrets via `gh`
#   --venue-url <url>    SeatEngine venue URL to fetch from
#                        (default: https://www-vermontcomedyclub-com.seatengine.com/events)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
VENUE_URL="https://www-vermontcomedyclub-com.seatengine.com/events"
SET_GH_SECRET=0

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --gh-secret) SET_GH_SECRET=1; shift ;;
    --venue-url) VENUE_URL="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

echo "Fetching SeatEngine events page: $VENUE_URL"

# Step 1: Get the events page and find a show detail URL
# The cart bundle is only loaded on show detail pages, not the events listing.
EVENTS_HTML=$(curl -s --compressed "$VENUE_URL")
SHOW_URL=$(echo "$EVENTS_HTML" \
  | grep -o 'https://[^"]*seatengine\.com/shows/[0-9]*' \
  | head -1)

if [[ -z "$SHOW_URL" ]]; then
  echo "Error: could not find a show URL on $VENUE_URL" >&2
  exit 1
fi
echo "Found show page: $SHOW_URL"

# Step 2: Find the cart bundle URL from the show detail page
SHOW_HTML=$(curl -s --compressed "$SHOW_URL")
CART_BUNDLE_URL=$(echo "$SHOW_HTML" \
  | grep -o 'https://cdn-new\.seatengine\.com/cart-[^"]*\.js' \
  | head -1)

if [[ -z "$CART_BUNDLE_URL" ]]; then
  echo "Error: could not find cart bundle URL on $SHOW_URL" >&2
  exit 1
fi
echo "Found cart bundle: $CART_BUNDLE_URL"

# Step 3: Extract APP_AUTH_TOKEN from the bundle
TOKEN=$(curl -s --compressed "$CART_BUNDLE_URL" \
  | grep -o 'APP_AUTH_TOKEN:"[^"]*"' \
  | grep -o '"[^"]*"$' \
  | tr -d '"')

if [[ -z "$TOKEN" ]]; then
  echo "Error: could not extract APP_AUTH_TOKEN from bundle" >&2
  exit 1
fi
echo "Extracted token: $TOKEN"

# Step 4: Verify the token works against the API
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "https://services.seatengine.com/api/v1/venues/21/shows" \
  -H "x-auth-token: $TOKEN")

if [[ "$HTTP_STATUS" != "200" ]]; then
  echo "Warning: token verification returned HTTP $HTTP_STATUS (expected 200)" >&2
else
  echo "Token verified against API (HTTP 200)"
fi

# Step 5: Write to .env
if grep -q "^SEATENGINE_AUTH_TOKEN=" "$ENV_FILE" 2>/dev/null; then
  # Update existing value (macOS-compatible sed)
  sed -i '' "s|^SEATENGINE_AUTH_TOKEN=.*|SEATENGINE_AUTH_TOKEN=$TOKEN|" "$ENV_FILE"
  echo "Updated SEATENGINE_AUTH_TOKEN in $ENV_FILE"
elif grep -q "SEATENGINE_AUTH_TOKEN" "$ENV_FILE" 2>/dev/null; then
  # Replace commented-out line
  sed -i '' "s|.*SEATENGINE_AUTH_TOKEN.*|SEATENGINE_AUTH_TOKEN=$TOKEN|" "$ENV_FILE"
  echo "Uncommented and set SEATENGINE_AUTH_TOKEN in $ENV_FILE"
else
  echo "SEATENGINE_AUTH_TOKEN=$TOKEN" >> "$ENV_FILE"
  echo "Appended SEATENGINE_AUTH_TOKEN to $ENV_FILE"
fi

# Step 6: Optionally push to GitHub secrets
if [[ "$SET_GH_SECRET" == "1" ]]; then
  if command -v gh &>/dev/null; then
    echo "$TOKEN" | gh secret set SEATENGINE_AUTH_TOKEN
    echo "Set SEATENGINE_AUTH_TOKEN in GitHub Actions secrets"
  else
    echo "Warning: gh CLI not found — skipping GitHub secret" >&2
  fi
fi

echo "Done."
