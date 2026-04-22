---
name: update-comedian-website
description: Update or clear a comedian's website URL in the database. Usage: /update-comedian-website <comedian name> [new URL | --clear]
allowed-tools: Bash, Read
---

# Update Comedian Website

Updates a comedian's website URL in the production database. Clears `website_scraping_url` when the root URL changes (since the old subpage would be stale).

## Usage

```
/update-comedian-website "John Mulaney" https://www.johnmulaney.com
/update-comedian-website "John Mulaney" --clear
```

## Arguments

- First argument: comedian name (exact or partial match)
- Second argument: new website URL, or `--clear` to remove the website

## Steps

### 1. Parse Arguments

Extract the comedian name and the new URL (or `--clear` flag) from the arguments.

If no arguments are provided, ask the user for the comedian name and new URL.

### 2. Look Up the Comedian

Run from `apps/scraper/`:

```bash
cd apps/scraper && .venv/bin/python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('.env')
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
cur.execute('''
    SELECT id, name, website, website_scraping_url
    FROM comedians
    WHERE LOWER(name) LIKE LOWER(%s)
    ORDER BY name
''', ('%<comedian_name>%',))
for row in cur.fetchall():
    print(f'{row[0]} | {row[1]} | {row[2] or \"(none)\"} | {row[3] or \"(none)\"}')
conn.close()
"
```

- If **zero matches**: report "No comedian found matching '<name>'" and stop.
- If **multiple matches**: show all matches and ask the user to pick one by ID.
- If **one match**: proceed with that comedian.

### 3. Confirm the Update

Show the current state and proposed change:

```
Comedian: <name>
Current website: <current URL or (none)>
Current scraping URL: <current scraping URL or (none)>
New website: <new URL or (clearing)>
```

Ask the user to confirm before proceeding.

### 4. Apply the Update

**If setting a new URL:**

```bash
cd apps/scraper && .venv/bin/python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('.env')
import psycopg2
conn = psycopg2.connect(
    host=os.environ['DATABASE_HOST'],
    user=os.environ['DATABASE_USER'],
    password=os.environ['DATABASE_PASSWORD'],
    dbname=os.environ['DATABASE_NAME'],
    port=int(os.environ.get('DATABASE_PORT', '5432')),
    sslmode='require'
)
conn.autocommit = True
cur = conn.cursor()
cur.execute('''
    UPDATE comedians
    SET website = %s,
        website_scraping_url = NULL,
        website_last_scraped = NULL,
        website_scrape_strategy = NULL
    WHERE id = %s
''', ('<new_url>', <comedian_id>))
print(f'Updated {cur.rowcount} row(s)')
conn.close()
"
```

Note: clears `website_scraping_url`, `website_last_scraped`, and `website_scrape_strategy` so the scraper will re-discover the correct subpage on next run.

**If clearing (`--clear`):**

```bash
cd apps/scraper && .venv/bin/python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('.env')
import psycopg2
conn = psycopg2.connect(
    host=os.environ['DATABASE_HOST'],
    user=os.environ['DATABASE_USER'],
    password=os.environ['DATABASE_PASSWORD'],
    dbname=os.environ['DATABASE_NAME'],
    port=int(os.environ.get('DATABASE_PORT', '5432')),
    sslmode='require'
)
conn.autocommit = True
cur = conn.cursor()
cur.execute('''
    UPDATE comedians
    SET website = NULL,
        website_scraping_url = NULL,
        website_last_scraped = NULL,
        website_scrape_strategy = NULL,
        website_discovery_source = NULL
    WHERE id = %s
''', (<comedian_id>,))
print(f'Cleared website for {cur.rowcount} row(s)')
conn.close()
"
```

### 5. Report

Print confirmation:

```
Updated <comedian name>:
  website: <old> → <new or (cleared)>
  website_scraping_url: cleared
  website_last_scraped: cleared
  website_scrape_strategy: cleared
```
