---
name: triage-nightly
description: Analyze scraper metrics and categorize failures into regressions, errors, and broken clubs with streak detection. Posts triage report to Discord.
---

# Triage Nightly Skill

Fetches up to 7 days of metrics JSON snapshots, compares them, and produces an actionable triage report categorizing clubs into three buckets: **regressions** (had shows yesterday, 0 today), **errors** (scraper failures), and **broken** (0 shows for N consecutive days).

## Arguments

Parse `ARGUMENTS`:
- If `--local` is present → set **local mode**
- If `--create-tasks` is present → set **create-tasks mode** (will auto-create tusk tasks for new regressions after the report)
- If neither flag is present → go to **Mode: GitHub** (with local fallback if `gh auth` is unavailable)
- Flags can be combined: `--local --create-tasks`

If local mode → go to **Mode: Local**; otherwise → go to **Mode: GitHub**

---

## Mode: GitHub

**Step 1 — Check gh auth:**
```bash
gh auth status 2>&1
```
If the command fails or prints "not logged in" → print a notice:
> `Warning: gh auth unavailable — falling back to local metrics in apps/scraper/metrics/`

Then go to **Mode: Local**.

**Step 2 — Find recent successful scheduled runs (up to 7):**
```bash
gh run list --workflow scraper-schedule.yml --limit 10 --json databaseId,conclusion,createdAt,headSha 2>&1
```
Filter to `conclusion == "success"`. Take up to 7 entries (newest first). Note their `databaseId` values.

**Step 3 — Download all artifacts in parallel:**
```bash
ARTIFACTS_DIR=$(mktemp -d)
for run_id in <id1> <id2> ... <idN>; do
  gh run download "$run_id" --name "scraper-dashboard-$run_id" --dir "$ARTIFACTS_DIR/$run_id" 2>&1 &
done
wait
```

**Step 4 — Locate metrics files:**
For each downloaded run, find the metrics JSON:
```bash
ls "$ARTIFACTS_DIR/<run_id>/metrics/metrics_"*.json 2>/dev/null | head -1
```
Collect all found file paths into a list (newest first, matching the run order). If no files are found at all → fall back to **Mode: Local**.

Set `METRICS_FILES` to the space-separated list of paths (newest first). Go to **Render Report**.

---

## Mode: Local

Find up to 7 newest local metrics files:
```bash
ls apps/scraper/metrics/metrics_*.json 2>/dev/null | sort -r | head -7
```
If **no files** found → print:
> `No metrics files found in apps/scraper/metrics/ — run a scrape first or use /scraper-nightly to fetch from GH Actions.`

Stop.

Set `METRICS_FILES` to the list of paths (newest first). Go to **Render Report**.

---

## Render Report

Run the following inline Python, passing all metrics file paths as arguments (newest first):

```bash
python3 - $METRICS_FILES << 'PYEOF'
import sys, json, os
from collections import defaultdict

# ── Load all metrics files (newest first) ──────────────────────────────────
def load_metrics(path):
    if not path or not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

days = []
for fp in sys.argv[1:]:
    data = load_metrics(fp)
    if not data:
        continue
    date = os.path.basename(fp).replace("metrics_", "").replace(".json", "")[:8]
    clubs = {c["club_id"]: c for c in data.get("per_club_stats", []) if "club_id" in c}
    days.append({"date": date, "clubs": clubs, "session": data.get("session", {})})

if not days:
    print("ERROR: Could not load any metrics files")
    sys.exit(1)

current = days[0]
previous = days[1] if len(days) > 1 else None
cur_clubs = current["clubs"]
exported_at = current["session"].get("exported_at", "unknown")

# ── Categorize: Regression / Error / Broken ────────────────────────────────
regressions = []  # had shows yesterday, 0 today (silent parser/site break)
errors = []       # actual scraper error (HTTP 403, parse failure, etc.)
broken = []       # 0 shows for 2+ consecutive days (chronic)

for cid, club in cur_clubs.items():
    name = club.get("club", "?")
    success = club.get("success", True)
    error = club.get("error") or ""
    num_shows = club.get("num_shows", 0)

    prev_club = previous["clubs"].get(cid) if previous else None
    prev_shows = prev_club.get("num_shows", 0) if prev_club else 0
    prev_success = prev_club.get("success", True) if prev_club else True

    # Compute streak: consecutive days of 0 shows or error, looking backwards
    zero_streak = 0
    for day in days:
        c = day["clubs"].get(cid)
        if c and (not c.get("success", True) or c.get("num_shows", 0) == 0):
            zero_streak += 1
        else:
            break

    if not success:
        tag = "NEW" if prev_success else f"{zero_streak}d"
        errors.append({"name": name, "id": cid, "error": error, "tag": tag, "streak": zero_streak})
    elif num_shows == 0:
        if prev_shows > 0:
            regressions.append({"name": name, "id": cid, "prev_shows": prev_shows})
        elif zero_streak >= 2:
            broken.append({"name": name, "id": cid, "streak": zero_streak})

# ── Render ──────────────────────────────────────────────────────────────────
total_clubs = len(cur_clubs)
total_with_shows = len([c for c in cur_clubs.values() if c.get("success", True) and c.get("num_shows", 0) > 0])
total_empty = len([c for c in cur_clubs.values() if c.get("success", True) and c.get("num_shows", 0) == 0])
total_errored = len([c for c in cur_clubs.values() if not c.get("success", True)])

print(f"\n{'='*64}")
print(f"  SCRAPER TRIAGE — {exported_at[:10]} ({len(days)}-day lookback)")
print(f"{'='*64}")
print(f"  {total_clubs} clubs | {total_with_shows} with shows | {total_empty} empty | {total_errored} errored")
print()

# ── 1. REGRESSIONS (had shows yesterday, 0 today) ─────────────────────────
print(f"## REGRESSIONS ({len(regressions)}) — had shows yesterday, 0 today")
print(f"{'─'*64}")
if regressions:
    for r in sorted(regressions, key=lambda x: -x["prev_shows"]):
        safe_name = r["name"].replace("'", "'\\''")
        print(f"  {r['name']} (id={r['id']}): {r['prev_shows']} → 0")
        print(f"    Repro: cd apps/scraper && make scrape-club CLUB='{safe_name}'")
        print()
else:
    print("  None")
print()

# ── 2. ERRORS (scraper failures) ──────────────────────────────────────────
print(f"## ERRORS ({len(errors)})")
print(f"{'─'*64}")
if errors:
    for e in sorted(errors, key=lambda x: x["name"]):
        err_short = e["error"][:80] + "..." if len(e["error"]) > 80 else e["error"]
        safe_name = e["name"].replace("'", "'\\''")
        print(f"  [{e['tag']}] {e['name']} (id={e['id']}): {err_short}")
        if e["tag"] == "NEW":
            print(f"    Repro: cd apps/scraper && make scrape-club CLUB='{safe_name}'")
            print()
else:
    print("  None")
print()

# ── 3. BROKEN (0 shows for N consecutive days) ────────────────────────────
print(f"## BROKEN ({len(broken)}) — 0 shows for 2+ consecutive days")
print(f"{'─'*64}")
if broken:
    by_streak = defaultdict(list)
    for b in broken:
        by_streak[b["streak"]].append(b)
    for streak in sorted(by_streak.keys(), reverse=True):
        clubs_in_streak = sorted(by_streak[streak], key=lambda x: x["name"])
        names = ", ".join(c["name"] for c in clubs_in_streak[:5])
        extra = f" ...and {len(clubs_in_streak)-5} more" if len(clubs_in_streak) > 5 else ""
        print(f"  {streak} days ({len(clubs_in_streak)} clubs): {names}{extra}")
else:
    print("  None")
print()
print(f"{'='*64}")

# ── Build Discord message ───────────────────────────────────────────────────
lines = []
icon = "🔴" if regressions or any(e["tag"] == "NEW" for e in errors) else ("🟡" if errors else "🟢")
lines.append(f"{icon} **Scraper Triage** — {exported_at[:10]} ({len(days)}d lookback)")
lines.append(f"{total_with_shows}/{total_clubs} with shows | {total_empty} empty | {total_errored} errored")
if regressions:
    lines.append(f"\n**Regressions ({len(regressions)}):**")
    for r in sorted(regressions, key=lambda x: -x["prev_shows"])[:10]:
        lines.append(f"- {r['name']}: {r['prev_shows']} → 0")
    if len(regressions) > 10:
        lines.append(f"  ...and {len(regressions)-10} more")
new_errors = [e for e in errors if e["tag"] == "NEW"]
old_errors = [e for e in errors if e["tag"] != "NEW"]
if new_errors:
    lines.append(f"\n**New Errors ({len(new_errors)}):**")
    for e in new_errors[:10]:
        err_short = e["error"][:60] + "..." if len(e["error"]) > 60 else e["error"]
        lines.append(f"- {e['name']}: {err_short}")
if old_errors:
    lines.append(f"\n**Persistent Errors ({len(old_errors)}):** " + ", ".join(e["name"] for e in old_errors[:8]))
    if len(old_errors) > 8:
        lines.append(f"  ...and {len(old_errors)-8} more")
if broken:
    lines.append(f"\n**Broken ({len(broken)}):** 0 shows for 2+d")

discord_msg = "\n".join(lines)
if len(discord_msg) > 1950:
    discord_msg = discord_msg[:1950] + "\n...truncated"

print(f"\n--- DISCORD MESSAGE ---")
print(discord_msg)
print(f"--- END DISCORD MESSAGE ---")

# ── Machine-readable outputs for --create-tasks ───────────────────────────
print(f"\n--- REGRESSIONS_JSON ---")
print(json.dumps(regressions))
print(f"--- END REGRESSIONS_JSON ---")

print(f"\n--- NEW_ERRORS_JSON ---")
print(json.dumps([{"name": e["name"], "id": e["id"], "error": e["error"]} for e in errors if e["tag"] == "NEW"]))
print(f"--- END NEW_ERRORS_JSON ---")
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

For now, display the Discord message block to the user and suggest they copy-paste it to the channel — or skip the Discord step if there are zero regressions and zero new errors (nothing actionable to alert on).

---

## Create Tasks for Regressions

**Skip this section entirely** if `--create-tasks` was NOT passed in arguments. The report-only behavior (no task creation) is the default.

If `--create-tasks` was passed:

1. Extract the JSON arrays from the Python output:
   - `REGRESSIONS_JSON` — clubs that had shows yesterday but returned 0 today (silent break)
   - `NEW_ERRORS_JSON` — clubs that started erroring after being OK yesterday

2. If both arrays are empty, print:
   > No new regressions — no tasks to create.

   Stop.

3. **For each regression** (from `REGRESSIONS_JSON`), create a task:

   ```bash
   tusk task-insert \
     "Investigate scraper regression: <club_name>" \
     "Scraper for <club_name> (club id=<club_id>) returned 0 shows after having <prev_shows> shows in the previous nightly run. No error was reported — the scraper ran successfully but found nothing. This may indicate a site redesign, changed selectors, or a temporary calendar gap.\n\nNightly run: <head_sha> (GHA run <run_id>) — check \`git log <head_sha>..HEAD\` for intervening fixes before investigating.\n\nReproduction:\ncd apps/scraper && make scrape-club CLUB='<club_name>'" \
     --priority High \
     --domain scraper \
     --task-type bug \
     --assignee scraper \
     --complexity XS \
     --criteria "Scraper returns non-zero shows or club confirmed to have no upcoming shows: cd apps/scraper && make scrape-club CLUB='<club_name>'"
   ```

4. **For each new error** (from `NEW_ERRORS_JSON`), create a task:

   ```bash
   tusk task-insert \
     "Fix scraper error: <club_name>" \
     "Scraper for <club_name> (club id=<club_id>) started failing after being OK in the previous nightly run.\n\nError: <error_message>\n\nNightly run: <head_sha> (GHA run <run_id>) — check \`git log <head_sha>..HEAD\` for intervening fixes before investigating.\n\nReproduction:\ncd apps/scraper && make scrape-club CLUB='<club_name>'" \
     --priority High \
     --domain scraper \
     --task-type bug \
     --assignee scraper \
     --complexity XS \
     --criteria "Scraper runs without errors: cd apps/scraper && make scrape-club CLUB='<club_name>'"
   ```

   Replace `<club_name>`, `<club_id>`, `<prev_shows>`, and `<error_message>` with values from the JSON entries. Escape single quotes in club names for shell safety.

5. After all tasks are created, print a summary:
   > Created **N** task(s): **X** regressions, **Y** new errors.

   List the task IDs and club names.

**Important constraints:**
- Only **regressions** (>0 shows → 0) and **new errors** (OK → error) generate tasks — these just broke.
- **Persistent errors** (erroring for 2+ days) do NOT generate tasks — already known.
- **Broken** clubs (0 shows for 2+ consecutive days) do NOT generate tasks — chronic issue, not a new regression.
- Clubs with 0 shows and no previous data do NOT generate tasks — no baseline to compare against.
