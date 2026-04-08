---
name: onboard-club
description: Check if clubs are already in the DB, then create onboarding tasks for new ones. Usage: /onboard-club <club1>, <club2>, ...
allowed-tools: Bash, Read, Skill
---

# Onboard Club

Checks whether one or more comedy clubs are already tracked in the database. For any that are not, creates structured onboarding tasks via `/create-task`.

## Usage

```
/onboard-club Punch Line Sacramento
/onboard-club Punch Line Sacramento, Cleveland Improv, Largo at the Coronet
```

## Arguments

- One or more club names, comma-separated

If no names are provided, ask:

> Which club(s) would you like to onboard? You can provide multiple names separated by commas.

## Steps

### 1. Parse Club Names

Split the input on commas and trim whitespace from each name. This produces a list of club names to process.

### 2. Check All Clubs Against the Database (MANDATORY — must run before ANY task creation)

**CRITICAL**: This step MUST execute successfully before proceeding. If the query fails, STOP and report the error — do NOT skip ahead to task creation.

Run the query below. It checks each input name against the clubs table using fuzzy matching (LIKE with wildcards) AND also extracts individual significant words from each name to catch partial matches (e.g., input "Syracuse Funny Bone" will match a DB entry called "Funny Bone Syracuse").

```bash
cd apps/scraper && .venv/bin/python3 -c "
import os, sys, json
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
names = <python_list_of_club_names>
# Words to ignore when doing keyword matching (too generic to be meaningful)
STOP_WORDS = {'the', 'a', 'an', 'at', 'in', 'of', 'and', 'comedy', 'club', 'theater', 'theatre', 'improv', 'lounge', 'bar', 'cafe'}
results = {}
for name in names:
    # Primary: fuzzy match on the full name
    cur.execute('''
        SELECT id, name, city, state, website, scraper
        FROM clubs
        WHERE LOWER(name) LIKE LOWER(%s)
        ORDER BY name
    ''', ('%' + name.strip() + '%',))
    rows = cur.fetchall()
    # Secondary: keyword match — extract significant words and search for each
    if not rows:
        words = [w for w in name.strip().split() if w.lower() not in STOP_WORDS and len(w) > 2]
        if words:
            # Match clubs whose name contains ALL significant words
            conditions = ' AND '.join(['LOWER(name) LIKE LOWER(%s)'] * len(words))
            params = ['%' + w + '%' for w in words]
            cur.execute(f'''
                SELECT id, name, city, state, website, scraper
                FROM clubs
                WHERE {conditions}
                ORDER BY name
            ''', params)
            rows = cur.fetchall()
    results[name] = [{'id': r[0], 'name': r[1], 'city': r[2], 'state': r[3], 'website': r[4], 'scraper': r[5]} for r in rows]
conn.close()
print(json.dumps(results))
"
```

Replace `<python_list_of_club_names>` with the actual Python list (e.g., `['Punch Line Sacramento', 'Cleveland Improv']`).

**You MUST read and parse the JSON output.** Any club with a non-empty match array is already onboarded and MUST NOT have a task created for it.

### 3. Categorize Results

Sort each club into one of two lists based on the query output from step 2:

- **Already onboarded**: the query returned one or more matches (non-empty array `[...]`)
- **New clubs**: the query returned no matches (empty array `[]`)

**If ALL clubs are already onboarded**, skip steps 4–5 and go directly to step 6 (Summary).

### 4. Report Existing Clubs

If any clubs are already onboarded, show them in a table:

> **Already in the database (skipped):**
>
> | Input | Matched Club | ID | Location | Scraper |
> |-------|--------------|----|----------|---------|
> | ... | ... | ... | ... | ... |

### 5. Create Onboarding Tasks for New Clubs

For each new club, invoke `/create-task` with:

```
Onboard <club name> to the clubs database.

Discovery source: manual request via /onboard-club.

Acceptance criteria:
1. Club record exists in the clubs table with correct name, city, state, timezone, and website
2. Scraper type is set and scraper produces show records
3. At least one successful scrape run with shows persisted to the database
```

When there are **multiple new clubs**, pass them all to `/create-task` in a single invocation as a batch:

```
Onboard the following clubs to the clubs database:

1. <club name 1>
2. <club name 2>
3. <club name 3>

Discovery source: manual request via /onboard-club.

For each club, acceptance criteria:
1. Club record exists in the clubs table with correct name, city, state, timezone, and website
2. Scraper type is set and scraper produces show records
3. At least one successful scrape run with shows persisted to the database
```

`/create-task` will handle decomposition into individual tasks, deduplication, and insertion.

### 6. Summary

Print a final summary:

```
Onboard Club Summary
━━━━━━━━━━━━━━━━━━━
Checked:  <total count>
Skipped:  <already onboarded count> (already in DB)
Created:  <new task count> tasks
```
