---
name: scraper-nightly
description: Surface nightly scraper run metrics — fetches latest GH Actions artifact or reads local metrics files. Usage: /scraper-nightly [--local]
allowed-tools: Bash
---

# Scraper Nightly Skill

Fetches the latest nightly scraper run and prints an actionable metrics report inline.

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
> `⚠  gh auth unavailable — falling back to local metrics in apps/scraper/metrics/`

Then go to **Mode: Local**.

**Step 2 — Find the latest scheduled run:**
```bash
gh run list --workflow scraper-schedule.yml --limit 5 --json databaseId,conclusion,createdAt,displayTitle 2>&1
```
Parse the JSON array. Take the first entry (most recent). Note its `databaseId`, `conclusion`, and `createdAt`.

**Step 3 — Download the artifact:**
```bash
TMPDIR=$(mktemp -d)
gh run download <databaseId> --name scraper-dashboard-<databaseId> --dir "$TMPDIR" 2>&1
```
If download fails (artifact expired, not found) → print:
> `⚠  Artifact not available for run <databaseId> — falling back to local metrics`

Then go to **Mode: Local**.

**Step 4 — Locate metrics file:**
```bash
ls "$TMPDIR/apps/scraper/metrics/metrics_"*.json 2>/dev/null | sort | tail -1
```
If no file found → try `ls "$TMPDIR/metrics_"*.json 2>/dev/null | sort | tail -1`.
If still none → fall back to **Mode: Local**.

Set `METRICS_FILE` to the found path and go to **Render Report**.

---

## Mode: Local

Find the newest local metrics file:
```bash
ls apps/scraper/metrics/metrics_*.json 2>/dev/null | sort | tail -1
```
If none found → print:
> `❌  No metrics files found in apps/scraper/metrics/ — run a scrape first`
Stop.

Set `METRICS_FILE` to the found path and go to **Render Report**.

---

## Render Report

Run the following inline Python, substituting `$METRICS_FILE` with the actual path:

```bash
python3 - "$METRICS_FILE" << 'PYEOF'
import sys, json, os, glob
from datetime import datetime, timezone

path = sys.argv[1]
d = json.load(open(path))

# ── helpers ──────────────────────────────────────────────────────────────────
def fmt_dur(secs):
    m, s = divmod(int(secs), 60)
    return f"{m}m {s}s" if m else f"{s}s"

def pct(n, total):
    return f"{n/total*100:.1f}%" if total else "n/a"

def delta_str(new, old):
    if old is None: return ""
    diff = new - old
    return f" (+{diff})" if diff > 0 else (f" ({diff})" if diff < 0 else " (±0)")

# ── load prior snapshot for trend ────────────────────────────────────────────
metrics_dir = os.path.dirname(path)
all_files = sorted(glob.glob(os.path.join(metrics_dir, "metrics_*.json")))
prior = None
if len(all_files) >= 2:
    try:
        idx = all_files.index(path)
        if idx > 0:
            prior = json.load(open(all_files[idx - 1]))
    except Exception:
        prior = None

# ── parse ─────────────────────────────────────────────────────────────────────
sess = d.get("session", {})
shows = d.get("shows", {})
clubs_agg = d.get("clubs", {})
per_club = d.get("per_club_stats", [])
err_details = d.get("error_details", [])

exported_at = sess.get("exported_at", "")
dur = sess.get("duration_seconds", 0)
try:
    dt = datetime.fromisoformat(exported_at)
    run_date = dt.strftime("%Y-%m-%d %H:%M UTC")
except Exception:
    run_date = exported_at

processed = clubs_agg.get("processed", 0)
successful = clubs_agg.get("successful", 0)
failed_clubs = clubs_agg.get("failed", 0)
success_rate = d.get("success_rate", 0)
overall_ok = failed_clubs == 0 and shows.get("scraped", 0) > 0

# ── 1. HEADER ─────────────────────────────────────────────────────────────────
status_icon = "✅" if overall_ok else "❌"
print(f"\n{'═'*64}")
print(f"  SCRAPER NIGHTLY REPORT  {status_icon}  {run_date}")
print(f"{'═'*64}")
print(f"  Duration     {fmt_dur(dur)}")
print(f"  Success rate {success_rate:.1f}%")
print(f"  Source       {os.path.basename(path)}")

# ── 2. THROUGHPUT ─────────────────────────────────────────────────────────────
print(f"\n── Throughput {'─'*48}")
scraped   = shows.get("scraped", 0)
inserted  = shows.get("inserted", 0)
updated   = shows.get("updated", 0)
failed_s  = shows.get("failed_save", 0)
dedup     = shows.get("skipped_dedup", 0)
val_fail  = shows.get("validation_failed", 0)
db_errs   = shows.get("db_errors", 0)
print(f"  Scraped          {scraped:>6}")
print(f"  Inserted         {inserted:>6}")
print(f"  Updated          {updated:>6}")
print(f"  Failed save      {failed_s:>6}")
print(f"  Dedup skips      {dedup:>6}")
print(f"  Validation fails {val_fail:>6}")
print(f"  DB errors        {db_errs:>6}")

# ── 3. CLUB HEALTH ────────────────────────────────────────────────────────────
print(f"\n── Club Health {'─'*48}")
print(f"  Processed   {processed:>5}")
print(f"  Successful  {successful:>5}  ({pct(successful, processed)})")
print(f"  Failed      {failed_clubs:>5}  ({pct(failed_clubs, processed)})")

failed_list = [c for c in per_club if not c.get("success", True)]
if failed_list:
    print(f"\n  Failed clubs:")
    for c in failed_list[:10]:
        err = c.get("error") or "unknown error"
        short_err = err[:80] + "…" if len(err) > 80 else err
        print(f"    ✗ {c['club']}: {short_err}")
    if len(failed_list) > 10:
        print(f"    … and {len(failed_list)-10} more")

# ── 4. ZERO-SHOW CLUBS ────────────────────────────────────────────────────────
zero_show = [c for c in per_club if c.get("success", True) and c.get("num_shows", 0) == 0]
print(f"\n── Zero-Show Clubs (potential regressions) {'─'*20}")
if zero_show:
    for c in zero_show:
        print(f"  ⚠  {c['club']}  (id={c.get('club_id','?')})")
else:
    print("  ✓ All successful clubs returned shows")

# ── 5. SLOW CLUBS ─────────────────────────────────────────────────────────────
print(f"\n── Slow Clubs (top 5 by execution time) {'─'*23}")
slowest = sorted(per_club, key=lambda c: c.get("execution_time", 0), reverse=True)[:5]
for c in slowest:
    t = c.get("execution_time", 0)
    print(f"  {fmt_dur(t):>8}  {c['club']}")

# ── 6. ERROR DETAILS ──────────────────────────────────────────────────────────
print(f"\n── Error Details {'─'*46}")
if err_details:
    for e in err_details[:15]:
        club = e.get("club", "?")
        msg = e.get("error", "")
        short = msg[:90] + "…" if len(msg) > 90 else msg
        print(f"  • {club}: {short}")
    if len(err_details) > 15:
        print(f"  … and {len(err_details)-15} more")
else:
    print("  ✓ No errors recorded")

# ── 7. TREND ──────────────────────────────────────────────────────────────────
print(f"\n── Trend vs Previous Run {'─'*38}")
if prior:
    p_shows = prior.get("shows", {})
    p_clubs = prior.get("clubs", {})
    p_scraped = p_shows.get("scraped", 0)
    p_processed = p_clubs.get("processed", 0)
    p_failed = p_clubs.get("failed", 0)
    print(f"  Shows scraped   {scraped:>6}{delta_str(scraped, p_scraped)}")
    print(f"  Clubs processed {processed:>5}{delta_str(processed, p_processed)}")
    print(f"  Clubs failed    {failed_clubs:>5}{delta_str(failed_clubs, p_failed)}")
else:
    print("  No prior snapshot available for comparison")

print(f"\n{'═'*64}\n")
PYEOF
```

Print the rendered output to the user verbatim. No additional commentary needed unless errors occurred during the data-fetch steps.
