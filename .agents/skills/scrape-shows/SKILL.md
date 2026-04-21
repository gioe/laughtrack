---
name: scrape-shows
description: Run the show scraper for all venues or a specific club. Usage: /scrape-shows [--club "Name"] [--club-id 123] [--types "type1,type2"] [--interactive]
allowed-tools: Bash
---

# Scrape Shows Skill

Runs the show scraper via `bin/scrape` from the repo root. Prints output inline.

## Arguments

Parse `ARGUMENTS`:
- `--club "Name"` → scrape a single venue by name → **Mode: Club**
- `--club-id 123` → scrape a single venue by DB ID → **Mode: Club ID**
- `--types "t1,t2"` → scrape by scraper type(s) in parallel → **Mode: Types**
- `--interactive` → launch interactive venue selector → **Mode: Interactive**
- _(no args)_ → scrape all venues → **Mode: All**

---

## Mode: All

```bash
./bin/scrape --all
```

---

## Mode: Club

Extract the club name from the `--club "..."` argument, then run:

```bash
./bin/scrape "<name>"
```

---

## Mode: Club ID

Extract the numeric ID from `--club-id`, then run:

```bash
./bin/scrape --id <id>
```

---

## Mode: Types

Extract the types string from `--types "..."`, then run:

```bash
./bin/scrape --types "<types>"
```

---

## Mode: Interactive

`bin/scrape` does not support interactive mode directly. Fall back to:

```bash
cd apps/scraper && make scrape-interactive
```

---

## Output

Stream and print all command output verbatim. When the command finishes, print a one-line summary:
- If exit code 0: `✓ Scrape complete.`
- If exit code non-zero: `✗ Scrape exited with code <N> — check output above for errors.`

## Verifying a Fix

To see per-target fetch results and confirm a fix is working, set `LAUGHTRACK_LOG_CONSOLE_LEVEL=INFO` explicitly:

```bash
LAUGHTRACK_LOG_CONSOLE_LEVEL=INFO ./bin/scrape "<name>"
```

This is useful after fixing rate-limit or 503 issues — the INFO log will show lines like `Successfully fetched data from N/M targets` and each per-target fetch result.
