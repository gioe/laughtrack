---
name: gh-run
description: Inspect a GitHub Actions run — prints header, per-job breakdown, and categorized failure insights. Usage: /gh-run [run-id]
allowed-tools: Bash
---

# GH Run Skill

Fetches GitHub Actions run metadata and failure logs via the `gh` CLI and renders
an inline structured report.

## Arguments

Parse `ARGUMENTS`:
- If a numeric run ID is present (e.g. `/gh-run 12345678`) → go to **Mode: Single Run**
- If empty → go to **Mode: List Runs**

---

## Step 1 — Check gh auth

```bash
gh auth status 2>&1
```

If the command exits non-zero or output contains "not logged in" / "no credentials":
> `❌  gh auth unavailable — run 'gh auth login' before using this skill`

Stop.

---

## Step 2 — Detect repo

```bash
git remote get-url origin 2>&1
```

Extract `OWNER/REPO` from the URL:
- SSH format: `git@github.com:OWNER/REPO.git` → strip `git@github.com:` and `.git`
- HTTPS format: `https://github.com/OWNER/REPO.git` or `https://github.com/OWNER/REPO`
  → strip scheme and `.git`

If the remote URL is not a GitHub URL or parsing fails → print:
> `❌  Could not detect GitHub repo from git remote. Is this a GitHub repo?`

Stop.

---

## Mode: List Runs

Fetch the 10 most recent runs across all workflows:

```bash
gh run list --repo OWNER/REPO --limit 10 --json databaseId,workflowName,headBranch,conclusion,createdAt,status 2>&1
```

Parse the JSON array and print a compact table:

```
Recent GitHub Actions runs for OWNER/REPO:

  #   RUN ID       WORKFLOW                    BRANCH          STATUS      CONCLUSION
  1.  <id>         <workflowName>              <headBranch>    <status>    <conclusion or "—">
  2.  ...
```

Use icons for conclusion: `✅` success, `❌` failure, `⚠️` cancelled/skipped, `⏳` (no conclusion, in-progress).

Then prompt:
> Reply with `/gh-run <run-id>` to inspect a specific run.

Stop (wait for user to provide a run ID).

---

## Mode: Single Run

### Fetch run metadata

```bash
gh run view RUNID --repo OWNER/REPO --json databaseId,workflowName,headBranch,conclusion,createdAt,updatedAt,url,jobs 2>&1
```

Parse the JSON. Then run the inline Python report below, passing the JSON via a temp file.

### Render Report

Save the JSON output to a temp file and run:

```bash
RUN_JSON=$(gh run view RUNID --repo OWNER/REPO --json databaseId,workflowName,headBranch,conclusion,createdAt,updatedAt,url,jobs 2>&1)

# Save to temp file
TMPFILE=$(mktemp /tmp/gh-run-XXXXXX.json)
echo "$RUN_JSON" > "$TMPFILE"

python3 - "$TMPFILE" << 'PYEOF'
import sys, json, subprocess
from datetime import datetime, timezone

path = sys.argv[1]
data = json.load(open(path))

# ── helpers ──────────────────────────────────────────────────────────────────
def fmt_dur(start_str, end_str):
    try:
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        s = datetime.strptime(start_str, fmt).replace(tzinfo=timezone.utc)
        e = datetime.strptime(end_str, fmt).replace(tzinfo=timezone.utc)
        secs = int((e - s).total_seconds())
        m, s2 = divmod(secs, 60)
        return f"{m}m {s2}s" if m else f"{s2}s"
    except Exception:
        return "?"

def conclusion_icon(c):
    if not c:
        return "⏳"
    c = c.lower()
    if c in ("success",):
        return "✅"
    if c in ("failure",):
        return "❌"
    if c in ("cancelled", "skipped", "neutral"):
        return "⚠️ "
    return "❓"

# ── parse ─────────────────────────────────────────────────────────────────────
run_id   = data.get("databaseId", "?")
workflow = data.get("workflowName", "?")
branch   = data.get("headBranch", "?")
conclusion = data.get("conclusion", "")
created  = data.get("createdAt", "")
updated  = data.get("updatedAt", created)
url      = data.get("url", "")
jobs     = data.get("jobs", [])
duration = fmt_dur(created, updated)
icon     = conclusion_icon(conclusion)

# ── 1. HEADER ─────────────────────────────────────────────────────────────────
print(f"\n{'═'*68}")
print(f"  GH RUN {run_id}  {icon}  {(conclusion or 'in_progress').upper()}")
print(f"{'═'*68}")
print(f"  Workflow  {workflow}")
print(f"  Branch    {branch}")
print(f"  Duration  {duration}")
print(f"  URL       {url}")

# ── 2. PER-JOB BREAKDOWN ──────────────────────────────────────────────────────
print(f"\n── Jobs {'─'*59}")
if jobs:
    name_w = max(len(j.get("name","")) for j in jobs)
    name_w = max(name_w, 20)
    print(f"  {'JOB':<{name_w}}  {'STATUS':<12}  {'CONCLUSION'}")
    print(f"  {'─'*name_w}  {'─'*12}  {'─'*12}")
    for j in jobs:
        jname = j.get("name", "?")
        jstatus = j.get("status", "?")
        jconc = j.get("conclusion", "") or "—"
        ji = conclusion_icon(j.get("conclusion",""))
        print(f"  {jname:<{name_w}}  {jstatus:<12}  {ji} {jconc}")
else:
    print("  (no job details available)")

# ── 3. SUCCESS PATH ───────────────────────────────────────────────────────────
if conclusion and conclusion.lower() == "success":
    print(f"\n{'═'*68}")
    print(f"  ✅  All jobs passed — no failures to inspect.\n")
    sys.exit(0)

# ── 4. FAILURE ANALYSIS ───────────────────────────────────────────────────────
print(f"\n── Failure Analysis {'─'*46}")
sys.stdout.flush()
PYEOF

# Fetch failure logs only for failed/cancelled runs
CONCLUSION=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('conclusion',''))" "$TMPFILE")

if [ "$CONCLUSION" = "failure" ] || [ "$CONCLUSION" = "cancelled" ]; then
    echo "  Fetching failure logs..."
    LOGFILE=$(mktemp /tmp/gh-run-logs-XXXXXX.txt)
    gh run view RUNID --repo OWNER/REPO --log-failed > "$LOGFILE" 2>&1
    LOG_EXIT=$?

    python3 - "$LOGFILE" "$LOG_EXIT" << 'PYEOF2'
import sys, re

logfile = sys.argv[1]
log_exit = int(sys.argv[2])

try:
    raw = open(logfile).read()
except Exception as e:
    print(f"  ⚠  Could not read log file: {e}")
    sys.exit(0)

if log_exit != 0 or not raw.strip():
    print("  ⚠  No failure logs available (artifact may have expired)")
    print(f"\n{'═'*68}\n")
    sys.exit(0)

# ── Categorize failures ────────────────────────────────────────────────────────
categories = {
    "test_failure":   [],
    "import_error":   [],
    "oom":            [],
    "timeout":        [],
    "script_error":   [],
    "other":          [],
}

# Extract log lines (strip leading timestamp/job prefix if present)
lines = raw.splitlines()
meaningful = []
for line in lines:
    # gh run --log-failed format: "TIMESTAMP  JOB  STEP  MESSAGE"
    # strip up to 3 tab-separated prefix fields
    parts = line.split("\t", 3)
    content = parts[-1].strip() if parts else line.strip()
    if content:
        meaningful.append(content)

for line in meaningful:
    ll = line.lower()
    if re.search(r"assert(ion)?error|tests? (failed|error)|fail(ed|ure)|FAILED\b", line):
        categories["test_failure"].append(line)
    elif re.search(r"importerror|modulenotfounderror|cannot import|no module named", ll):
        categories["import_error"].append(line)
    elif re.search(r"out of memory|oom|memory (limit|exceeded|error)|killed", ll):
        categories["oom"].append(line)
    elif re.search(r"timed? ?out|timeout|exceeded.*time limit", ll):
        categories["timeout"].append(line)
    elif re.search(r"error:|exception:|traceback|syntax ?error|command (not found|failed)", ll):
        categories["script_error"].append(line)

# Deduplicate and cap
def unique_lines(lst, cap=8):
    seen = set()
    out = []
    for l in lst:
        key = l.strip()[:120]
        if key not in seen:
            seen.add(key)
            out.append(l)
        if len(out) >= cap:
            break
    return out

labels = {
    "test_failure": "Test Failures",
    "import_error": "Import Errors",
    "oom":          "Out-of-Memory",
    "timeout":      "Timeouts",
    "script_error": "Script / Exception Errors",
    "other":        "Other",
}

any_category = False
for key, label in labels.items():
    hits = unique_lines(categories[key])
    if hits:
        any_category = True
        print(f"\n  [{label}]")
        for h in hits:
            short = h[:110] + "…" if len(h) > 110 else h
            print(f"    • {short}")

if not any_category:
    # Show raw tail as fallback
    print("\n  [Raw log tail — no pattern matched]")
    for line in meaningful[-20:]:
        short = line[:110] + "…" if len(line) > 110 else line
        print(f"    {short}")

print(f"\n{'═'*68}\n")
PYEOF2

    rm -f "$LOGFILE"
else
    python3 - << 'PYEOF3'
print(f"  (run did not fail — skipping log fetch)\n{'═'*68}\n")
PYEOF3
fi

rm -f "$TMPFILE"
```

**Note:** Replace `RUNID` with the actual run ID and `OWNER/REPO` with the detected repo before executing the block above.

Print the rendered output verbatim. No additional commentary needed unless errors occurred during data-fetch steps.
