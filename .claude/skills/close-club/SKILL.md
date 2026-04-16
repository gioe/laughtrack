---
name: close-club
description: "Close a permanently-defunct club — sets status=closed, visible=false, closed_at=NOW(), and creates a Prisma migration. Usage: /close-club <club name or ID>"
allowed-tools: Bash, Read, Grep
---

# Close Club

Marks a club as permanently closed in the database: sets `status='closed'`,
`visible=false`, and `closed_at=NOW()`. Creates the corresponding Prisma migration
file and records it in `_prisma_migrations`.

Use this for **confirmed-defunct** venues — ones where multiple signals (Yelp CLOSED,
domain expired/parked, platform API 404, no social media activity) establish the
venue is gone for good.

For **reversible hiding** (duplicate under review, production-company rehoming,
data-quality pull), use `/hide-club` instead — it sets only `visible=false` and
leaves `status='active'`, allowing easy restoration.

## Usage

```
/close-club <club name or ID>
```

Examples:
- `/close-club 816`
- `/close-club Morty's Comedy Joint`

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
cur.execute(\"SELECT id, name, status, visible FROM clubs WHERE LOWER(name) LIKE LOWER(%s)\", ('%<name>%',))
for row in cur.fetchall():
    print(f'  id={row[0]}  name={row[1]}  status={row[2]}  visible={row[3]}')
conn.close()
"
```

If multiple matches are returned, ask the user to confirm which club ID to close.
If the club is already closed (`status='closed'`), inform the user and stop.

## Step 2: Close the Club

```bash
make -C "$(git rev-parse --show-toplevel)/apps/scraper" close-club ID=<club_id>
```

This command:
1. Sets `status = 'closed'`, `visible = false`, and `closed_at = NOW()` in the database
2. Creates a Prisma migration file at `apps/web/prisma/migrations/<timestamp>_close_<slug>/migration.sql`
3. Records the migration in `_prisma_migrations`

## Step 3: Report

Print the migration file path so it can be committed:

```
Club <id> (<name>) closed.
Migration: apps/web/prisma/migrations/<migration_name>/migration.sql
```

If this was invoked as part of a `/tusk` workflow, the migration file should be
committed using `tusk commit` with the appropriate task ID and criteria.
