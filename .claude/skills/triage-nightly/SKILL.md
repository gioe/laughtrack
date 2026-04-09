---
name: triage-nightly
description: Analyze scraper metrics and categorize failures into new, persistent, recovered, and provider-wide outages. Posts triage report to Discord.
allowed-tools: Bash, Read, mcp__discord__discord_fetch_messages
---

# Triage Nightly Skill

Fetches the latest two metrics JSON snapshots, compares them, and produces an actionable triage report categorizing clubs into: new failures, persistent failures, recoveries, and provider-wide outages.

## Arguments

Parse `ARGUMENTS`:
- If `--local` is present → go to **Mode: Local**
- Otherwise → go to **Mode: GitHub** (with local fallback if `gh auth` is unavailable)

---

## Mode: GitHub

**Step 1 — Check gh auth:**
```bash
gh auth status 2>&1
```
If the command fails or prints "not logged in" → print a notice:
> `Warning: gh auth unavailable — falling back to local metrics in apps/scraper/metrics/`

Then go to **Mode: Local**.

**Step 2 — Find the latest scheduled run:**
```bash
gh run list --workflow scraper-schedule.yml --limit 5 --json databaseId,conclusion,createdAt,displayTitle 2>&1
```
Parse the JSON array. Take the first entry (most recent). Note its `databaseId`.

**Step 3 — Download the artifact:**
```bash
ARTIFACTS_DIR=$(mktemp -d)
gh run download <databaseId> --name scraper-dashboard-<databaseId> --dir "$ARTIFACTS_DIR" 2>&1
```
If download fails → print:
> `Warning: Artifact not available for run <databaseId> — falling back to local metrics`

Then go to **Mode: Local**.

**Step 4 — Locate metrics file:**
```bash
ls "$ARTIFACTS_DIR/apps/scraper/metrics/metrics_"*.json 2>/dev/null | sort | tail -1
```
If no file found → try `ls "$ARTIFACTS_DIR/metrics_"*.json 2>/dev/null | sort | tail -1`.
If still none → fall back to **Mode: Local**.

Set `CURRENT_FILE` to the found path. For the previous file, also check the artifact directory for a second-to-last file:
```bash
ls "$ARTIFACTS_DIR/apps/scraper/metrics/metrics_"*.json 2>/dev/null | sort | tail -2 | head -1
```
If only one file is in the artifact, look for the previous file in local `apps/scraper/metrics/`. Set `PREVIOUS_FILE` to whatever is found (or leave empty if none).

Go to **Render Report**.

---

## Mode: Local

Find the two newest local metrics files:
```bash
ls apps/scraper/metrics/metrics_*.json 2>/dev/null | sort | tail -2
```
If **no files** found → print:
> `No metrics files found in apps/scraper/metrics/ — run a scrape first or use /scraper-nightly to fetch from GH Actions.`

Stop.

If **only one file** found → set `CURRENT_FILE` to it, leave `PREVIOUS_FILE` empty.
If **two files** found → set `CURRENT_FILE` to the newer one, `PREVIOUS_FILE` to the older one.

Go to **Render Report**.

---

## Render Report

Run the following inline Python, substituting `$CURRENT_FILE` and `$PREVIOUS_FILE` with actual paths (pass empty string for PREVIOUS_FILE if unavailable):

```bash
python3 - "$CURRENT_FILE" "$PREVIOUS_FILE" << 'PYEOF'
import sys, json, os

current_path = sys.argv[1]
previous_path = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else ""

def load_metrics(path):
    if not path or not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

current = load_metrics(current_path)
previous = load_metrics(previous_path)

if not current:
    print("ERROR: Could not load current metrics file")
    sys.exit(1)

cur_clubs = {c["club_id"]: c for c in current.get("per_club_stats", []) if "club_id" in c}
prev_clubs = {c["club_id"]: c for c in (previous or {}).get("per_club_stats", []) if "club_id" in c} if previous else {}

sess = current.get("session", {})
exported_at = sess.get("exported_at", "unknown")

# ── Categorize ──────────────────────────────────────────────────────────────
new_failures = []       # OK yesterday, failing today
persistent_failures = [] # failing both days
recoveries = []         # failing yesterday, OK today
cur_ok = []             # OK both days or new+OK

for cid, club in cur_clubs.items():
    name = club.get("club", "?")
    success = club.get("success", True)
    error = club.get("error") or ""
    num_shows = club.get("num_shows", 0)
    # Treat zero-show successes as soft failures for triage
    is_failing = not success

    prev = prev_clubs.get(cid)
    was_failing = prev is not None and not prev.get("success", True) if prev else None

    if is_failing:
        if was_failing:
            persistent_failures.append({"name": name, "id": cid, "error": error})
        elif was_failing is False:
            new_failures.append({"name": name, "id": cid, "error": error})
        elif was_failing is None:
            # No previous data — treat as new
            new_failures.append({"name": name, "id": cid, "error": error})
    else:
        if was_failing:
            recoveries.append({"name": name, "id": cid})

# ── Provider-wide outage detection ──────────────────────────────────────────
# Group current failures by error message prefix (first 60 chars) to detect patterns
from collections import Counter, defaultdict
error_groups = defaultdict(list)
all_failing = [c for c in cur_clubs.values() if not c.get("success", True)]
for c in all_failing:
    err = (c.get("error") or "unknown")[:80]
    error_groups[err].append(c)

provider_outages = []
for err_pattern, clubs_in_group in error_groups.items():
    if len(clubs_in_group) >= 3:  # At least 3 clubs with same error pattern
        pct = len(clubs_in_group) / max(len(all_failing), 1) * 100
        if pct >= 80 or len(clubs_in_group) >= 5:
            provider_outages.append({
                "error_pattern": err_pattern,
                "count": len(clubs_in_group),
                "clubs": [c.get("club", "?") for c in clubs_in_group[:5]],
                "pct_of_failures": pct,
            })

# ── Render ──────────────────────────────────────────────────────────────────
total_clubs = len(cur_clubs)
total_failed = len(all_failing)
total_ok = total_clubs - total_failed
success_rate = current.get("success_rate", 0)

print(f"\n{'='*64}")
print(f"  SCRAPER TRIAGE REPORT  —  {exported_at}")
print(f"{'='*64}")
print(f"  Clubs: {total_clubs} total | {total_ok} OK | {total_failed} failed | {success_rate:.1f}% success")
if previous:
    print(f"  Compared against: {os.path.basename(previous_path)}")
else:
    print(f"  Note: No previous run available for comparison — all failures shown as new")
print()

# ── 1. NEW FAILURES (high priority) ────────────────────────────────────────
print(f"## NEW FAILURES ({len(new_failures)})")
print(f"{'─'*64}")
if new_failures:
    for f in sorted(new_failures, key=lambda x: x["name"]):
        err_short = f["error"][:100] + "..." if len(f["error"]) > 100 else f["error"]
        print(f"  FAIL  {f['name']} (id={f['id']})")
        print(f"        Error: {err_short}")
        safe_name = f["name"].replace("'", "'\\''")
        print(f"        Repro: cd apps/scraper && make scrape-club CLUB='{safe_name}'")
        print()
else:
    print("  None — no new failures since last run\n")

# ── 2. PERSISTENT FAILURES ──────────────────────────────────────────────────
print(f"## PERSISTENT FAILURES ({len(persistent_failures)})")
print(f"{'─'*64}")
if persistent_failures:
    for f in sorted(persistent_failures, key=lambda x: x["name"]):
        err_short = f["error"][:80] + "..." if len(f["error"]) > 80 else f["error"]
        print(f"  {f['name']} (id={f['id']}): {err_short}")
else:
    print("  None\n")
print()

# ── 3. RECOVERIES ───────────────────────────────────────────────────────────
print(f"## RECOVERIES ({len(recoveries)})")
print(f"{'─'*64}")
if recoveries:
    for r in sorted(recoveries, key=lambda x: x["name"]):
        print(f"  OK  {r['name']} (id={r['id']})")
else:
    print("  None — no clubs recovered since last run")
print()

# ── 4. PROVIDER-WIDE OUTAGES ────────────────────────────────────────────────
print(f"## PROVIDER-WIDE OUTAGES ({len(provider_outages)})")
print(f"{'─'*64}")
if provider_outages:
    for o in provider_outages:
        print(f"  OUTAGE  {o['count']} clubs ({o['pct_of_failures']:.0f}% of failures)")
        print(f"          Pattern: {o['error_pattern']}")
        print(f"          Example clubs: {', '.join(o['clubs'])}")
        print()
else:
    print("  None — no provider-wide patterns detected")
print()

print(f"{'='*64}")

# ── Build Discord message ───────────────────────────────────────────────────
# Output a compact version suitable for Discord (2000 char limit)
lines = []
icon = "🔴" if new_failures else ("🟡" if persistent_failures else "🟢")
lines.append(f"{icon} **Scraper Triage** — {exported_at[:10]}")
lines.append(f"Clubs: {total_ok}/{total_clubs} OK ({success_rate:.1f}%)")
if new_failures:
    lines.append(f"\n**New Failures ({len(new_failures)}):**")
    for f in new_failures[:10]:
        err_short = f["error"][:60] + "..." if len(f["error"]) > 60 else f["error"]
        lines.append(f"- {f['name']} (id={f['id']}): {err_short}")
    if len(new_failures) > 10:
        lines.append(f"  ...and {len(new_failures)-10} more")
if persistent_failures:
    lines.append(f"\n**Persistent ({len(persistent_failures)}):** " + ", ".join(f["name"] for f in persistent_failures[:8]))
    if len(persistent_failures) > 8:
        lines.append(f"  ...and {len(persistent_failures)-8} more")
if recoveries:
    lines.append(f"\n**Recovered ({len(recoveries)}):** " + ", ".join(r["name"] for r in recoveries[:8]))
if provider_outages:
    for o in provider_outages:
        lines.append(f"\n**Outage:** {o['count']} clubs — {o['error_pattern'][:60]}")

discord_msg = "\n".join(lines)
# Truncate to Discord's 2000 char limit
if len(discord_msg) > 1950:
    discord_msg = discord_msg[:1950] + "\n...truncated"

print(f"\n--- DISCORD MESSAGE ---")
print(discord_msg)
print(f"--- END DISCORD MESSAGE ---")
PYEOF
```

Print the full console triage report to the user verbatim.

---

## Post to Discord

After the report renders, extract the text between `--- DISCORD MESSAGE ---` and `--- END DISCORD MESSAGE ---`.

Post it to the #laughtrack Discord channel (ID: `1480559611689046066`).

**How to post:** The Discord MCP currently has read-only tools. Use a webhook or ask the user to post manually. If a `discord_send` or similar MCP tool becomes available in the future, use it with:
- `channel_id`: `1480559611689046066`
- `content`: the extracted Discord message text

For now, display the Discord message block to the user and suggest they copy-paste it to the channel — or skip the Discord step if there are zero new failures (nothing actionable to alert on).
