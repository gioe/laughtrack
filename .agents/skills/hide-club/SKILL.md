---
name: hide-club
description: "Hide a club from the platform — sets visible=false, creates a Prisma migration, and records it. Usage: /hide-club <club name or ID>"
---

# Hide Club

Sets a club to `visible = false` in the database, creates the corresponding Prisma
migration file, and records it in `_prisma_migrations`.

**When to use `/hide-club` vs `/close-club`:**

- `/hide-club` — reversible hiding while the club's fate is still open. Use for:
  duplicate records pending merge, clubs being rehomed as production companies,
  venues temporarily pulled for data-quality review. Leaves `status='active'` and
  `closed_at=NULL` so the club can be restored by flipping `visible` back to `true`.
- `/close-club` — permanent closure for confirmed-defunct venues. Use when multiple
  signals establish the venue is gone (Yelp CLOSED, domain dead, platform API 404,
  no social media activity). Sets `status='closed'`, `visible=false`, and
  `closed_at=NOW()` — the richer metadata lets downstream reporting distinguish
  "dead" from "hidden pending review."

## Usage

```
/hide-club <club name or ID>
```

Examples:
- `/hide-club 413`
- `/hide-club BJ's Mobile Drive-In Theater`

## Step 1: Resolve the Club ID

If the argument is numeric, use it directly as the club ID.

If the argument is a name, look it up:

```bash
"$(git rev-parse --show-toplevel)/apps/scraper/.venv/bin/python3" -c "
import os, subprocess
from dotenv import load_dotenv
scraper_dir = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip() + '/apps/scraper'
load_dotenv(scraper_dir + '/.env')
import psycopg2
conn = psycopg2.connect(
    host=os.environ['DATABASE_HOST'],
    user=os.environ['DATABASE_USER'],
    password=os.environ['DATABASE_PASSWORD'],
    dbname=os.environ['DATABASE_NAME'],
    port=int(os.environ.get('DATABASE_PORT', '5432')),
    sslmode='require'
)
cur = conn.cursor()
cur.execute(\"SELECT id, name, visible FROM clubs WHERE LOWER(name) LIKE LOWER(%s)\", ('%<name>%',))
for row in cur.fetchall():
    print(f'  id={row[0]}  name={row[1]}  visible={row[2]}')
conn.close()
"
```

If multiple matches are returned, ask the user to confirm which club ID to hide.
If the club is already hidden (`visible=false`), inform the user and stop.

## Step 2: Hide the Club

```bash
make -C "$(git rev-parse --show-toplevel)/apps/scraper" hide-club ID=<club_id>
```

This works from any directory within the repo.

This command:
1. Sets `visible = false` in the database
2. Creates a Prisma migration file at `apps/web/prisma/migrations/<timestamp>_hide_<slug>/migration.sql`
3. Records the migration in `_prisma_migrations`

## Step 3: Report

Print the migration file path so it can be committed:

```
Club <id> (<name>) hidden.
Migration: apps/web/prisma/migrations/<migration_name>/migration.sql
```

If this was invoked as part of a `/tusk` workflow, the migration file should be
committed using `tusk commit` with the appropriate task ID and criteria.
