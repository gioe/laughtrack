#!/usr/bin/env bash
# Loads DISCORD_BOT_TOKEN from apps/scraper/.env and runs the MCP server
set -euo pipefail

REPO_ROOT="${PWD}"
ENV_FILE="$REPO_ROOT/apps/scraper/.env"

if [ -f "$ENV_FILE" ]; then
    export DISCORD_BOT_TOKEN=$(grep '^DISCORD_BOT_TOKEN=' "$ENV_FILE" | cut -d= -f2-)
fi

exec python3 "$REPO_ROOT/.claude/mcp/discord-mcp.py"
