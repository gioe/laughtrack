# Launchd setup for scheduled scrapes (macOS)

This guide shows how to install, run, check, and remove the LaunchAgent that schedules `make scrape-all` using a small wrapper script that activates your venv.

- Plist: `ops/launchd/com.gioe.laughtrack.scrape-all.plist`
- Wrapper: `scripts/launchd_run_scrape_all.zsh`
- Logs: `logs/launchd-scrape-all.out.log` and `logs/launchd-scrape-all.err.log`

## Prerequisites

- Ensure the wrapper is executable:

  ```zsh
  chmod +x scripts/launchd_run_scrape_all.zsh
  ```

- The wrapper expects a venv at `.venv/`. If yours differs, update the `source` line in the wrapper.
- Absolute paths are required in launchd jobs; the plist already uses them.

## Install and load the LaunchAgent

```zsh
# Copy the agent into your user LaunchAgents folder
cp ops/launchd/com.gioe.laughtrack.scrape-all.plist ~/Library/LaunchAgents/

# Load + enable the agent for your GUI session (idempotent)
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.gioe.laughtrack.scrape-all.plist 2>/dev/null || true
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.gioe.laughtrack.scrape-all.plist
launchctl enable gui/$(id -u)/com.gioe.laughtrack.scrape-all
```

## Start it now (one-off run)

```zsh
launchctl kickstart -k gui/$(id -u)/com.gioe.laughtrack.scrape-all
```

## Check status and logs

```zsh
# Status summary
launchctl print gui/$(id -u)/com.gioe.laughtrack.scrape-all | head -n 80

# Tail logs
tail -n 100 logs/launchd-scrape-all.out.log
tail -n 100 logs/launchd-scrape-all.err.log
```

## Change the schedule

- Edit `ops/launchd/com.gioe.laughtrack.scrape-all.plist` `StartCalendarInterval` (Hour/Minute) as desired.
- Reapply the agent:

  ```zsh
  launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.gioe.laughtrack.scrape-all.plist
  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.gioe.laughtrack.scrape-all.plist
  launchctl enable gui/$(id -u)/com.gioe.laughtrack.scrape-all
  ```

## Unload/disable (stop scheduling)

```zsh
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.gioe.laughtrack.scrape-all.plist
```

## Manual runs (without launchd)

```zsh
# DRY run: preview make commands without scraping
DRY_RUN=1 /bin/zsh scripts/launchd_run_scrape_all.zsh

# Real run
/bin/zsh scripts/launchd_run_scrape_all.zsh
```

## Troubleshooting

- PATH: launchd uses a minimal environment. The wrapper sets `PATH` and activates `.venv` before invoking `make scrape-all`.
- Permissions: ensure the wrapper is executable and the plist lives in `~/Library/LaunchAgents/`.
- Venv location: update the `source .venv/bin/activate` line if your venv is elsewhere.
- Logs: inspect `logs/launchd-scrape-all.err.log` for errors if a run fails.
- WorkingDirectory: set in the plist; commands run from the repo root.

## Notes

- The job runs daily at 02:30 by default; adjust in the plist.
- You can keep using `make scrape-all` interactively; launchd just automates it on a schedule.
