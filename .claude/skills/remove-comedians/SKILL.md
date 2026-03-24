---
name: remove-comedians
description: Batch-remove comedian records from the DB and add them to the deny list. Runs dry-run first, waits for explicit user confirmation, then executes. Usage: /remove-comedians [--name "Name"] [--names-file path]
allowed-tools: Bash
---

# Remove Comedians Skill

Removes comedian records from the database and permanently adds their names to
`comedian_deny_list` so they cannot be re-ingested by future scrapes.

Supported inputs: repeatable `--name` flags, a `--names-file` (one name per line,
`#` comments and blank lines ignored), or both combined.

## Arguments

Parse `ARGUMENTS`:
- `--name <name>` → one comedian name to remove (repeatable)
- `--names-file <path>` → path to a names file

## Steps

### 1. Always run dry-run first

```bash
cd apps/scraper && .venv/bin/python scripts/core/remove_comedians.py ARGUMENTS
```

This prints a status table without modifying the DB:

```
Name                                          Status          Lineup Items
---------------------------------------------------------------------------
John Doe                                      FOUND                      3
Jane Smith                                    NOT IN DB                  -
TBA                                           ALREADY DENIED             -

Dry-run: 1 FOUND, 1 NOT IN DB, 1 ALREADY DENIED. Pass --confirm to execute.
```

Status meanings:
- **FOUND** — comedian exists in DB; will be deleted with their lineup_items
- **NOT IN DB** — not in comedians table; still added to deny list on confirm (future-proofs against re-ingestion)
- **ALREADY DENIED** — already in deny list; skipped entirely

If all names are ALREADY DENIED the script exits immediately with "nothing to do."

### 2. Surface the table and wait for explicit confirmation

Show the output to the user. Do **not** proceed with `--confirm` until the user
explicitly approves (e.g. "yes", "confirm", "looks good", "do it").

If the user does not confirm, stop here. Never auto-confirm.

### 3. Execute on confirmation

```bash
cd apps/scraper && .venv/bin/python scripts/core/remove_comedians.py ARGUMENTS --confirm
```

This:
1. Deletes `lineup_items` rows then `comedian` records in a single transaction
2. Adds FOUND + NOT IN DB names to `comedian_deny_list` (idempotent)
3. Prints a summary of deleted records and added deny-list entries

Report the output to the user.
