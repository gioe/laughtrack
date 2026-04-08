---
name: onboard-club
description: Check if a club is already in the DB, then create an onboarding task if not. Usage: /onboard-club <club name>
allowed-tools: Bash, Read, Skill
---

# Onboard Club

Checks whether a comedy club is already tracked in the database. If not, creates a structured onboarding task via `/create-task`.

## Usage

```
/onboard-club Punch Line Sacramento
/onboard-club "Cleveland Improv"
```

## Arguments

- Club name (required): the venue name to check and potentially onboard

If no name is provided, ask:

> Which club would you like to onboard?

## Steps

### 1. Parse the Club Name

Extract the club name from the arguments after `/onboard-club`.

### 2. Check the Database

Search for the club by name (fuzzy match) against the clubs table:

```bash
cd apps/scraper && .venv/bin/python3 -c "
import os, sys
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
    SELECT id, name, city, state, website, scraper_type
    FROM clubs
    WHERE LOWER(name) LIKE LOWER(%s)
    ORDER BY name
''', ('%<club_name>%',))
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f'{r[0]} | {r[1]} | {r[2] or \"\"}, {r[3] or \"\"} | {r[4] or \"(no website)\"} | scraper: {r[5] or \"(none)\"}')
else:
    print('NO_MATCH')
conn.close()
"
```

Replace `<club_name>` with the actual club name.

### 3. Evaluate the Result

**If matches are found**: the club is already onboarded (or a very similar name exists). Report:

> **Already in the database:**
>
> | ID | Name | Location | Website | Scraper |
> |----|------|----------|---------|---------|
> | ... | ... | ... | ... | ... |
>
> No onboarding task created.

Then **stop**. Do not create a task.

**If `NO_MATCH` is returned**: the club is not in the database. Proceed to Step 4.

### 4. Create Onboarding Task

Invoke the `/create-task` skill with a structured onboarding description. Pass the following text:

```
Onboard <club name> to the clubs database.

Discovery source: manual request via /onboard-club.

Acceptance criteria:
1. Club record exists in the clubs table with correct name, city, state, timezone, and website
2. Scraper type is set and scraper produces show records
3. At least one successful scrape run with shows persisted to the database
```

The `/create-task` skill will handle decomposition, deduplication, domain/priority assignment, and insertion.

### 5. Report

After `/create-task` completes, confirm:

> Onboarding task created for **<club name>**.
