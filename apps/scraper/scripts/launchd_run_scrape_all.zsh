#!/bin/zsh
set -euo pipefail

# Ensure a reasonable PATH for non-interactive shells
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Move to repo root
cd /Users/mattgioe/Desktop/projects/laughtrack-scraper

# Activate venv if present (adjust path if your venv is elsewhere)
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

# Run the task (support DRY_RUN=1 to preview commands without executing)
if [[ "${DRY_RUN:-}" = "1" ]]; then
  echo "[launchd wrapper] DRY_RUN enabled — previewing make commands only"
  make -n scrape-all
else
  make scrape-all
fi
