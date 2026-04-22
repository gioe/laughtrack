---
name: scrape-shows
description: Run the show scraper for all venues or a specific club. Usage: /scrape-shows [--club "Name"] [--club-id 123] [--types "type1,type2"] [--interactive]
---

# Scrape Shows Skill

Runs the show scraper from `apps/scraper/` using the Make targets that exist in
this repo. Prints output inline.

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
cd apps/scraper && make scrape-all --no-print-directory 2>&1
```

---

## Mode: Club

Extract the club name from the `--club "..."` argument, then run:

```bash
cd apps/scraper && make scrape-club CLUB="<name>" --no-print-directory 2>&1
```

---

## Mode: Club ID

Extract the numeric ID from `--club-id`, then run:

```bash
cd apps/scraper && make scrape-club-id ID=<id> --no-print-directory 2>&1
```

---

## Mode: Types

Extract the types string from `--types "..."`, then run:

```bash
cd apps/scraper && make scrape-types TYPES="<types>" --no-print-directory 2>&1
```

---

## Mode: Interactive

Run the interactive selector directly from the scraper Makefile:

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
cd apps/scraper && LAUGHTRACK_LOG_CONSOLE_LEVEL=INFO make scrape-club CLUB="<name>" --no-print-directory 2>&1
```

This is useful after fixing rate-limit or 503 issues — the INFO log will show lines like `Successfully fetched data from N/M targets` and each per-target fetch result.
