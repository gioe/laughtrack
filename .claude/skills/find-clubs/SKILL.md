---
name: find-clubs
description: Discover comedy clubs in a city, compare against the known clubs DB, and create tasks for new ones. Usage: /find-clubs [city name]
allowed-tools: Bash, WebSearch
---

# Find Clubs Skill

Discovers comedy clubs in a city via web search, compares against the known clubs database, and creates scraper onboarding tasks for any new clubs the user confirms.

## Step 1: Capture City Input

The city is provided after `/find-clubs`. If no city was given, ask:

> Which city should I search for comedy clubs in?

Wait for the user to respond before continuing.

## Step 2: Query Known Clubs from DB

Fetch all club names currently in the database:

```bash
cd /Users/mattgioe/Desktop/projects/laughtrack/apps/scraper && .venv/bin/python3 -c "
import sys
sys.path.insert(0, 'src')
from dotenv import load_dotenv
load_dotenv('.env')
from laughtrack.infrastructure.database.connection import create_connection
conn = create_connection()
cur = conn.cursor()
cur.execute('SELECT name FROM clubs ORDER BY name')
rows = cur.fetchall()
print('\n'.join(r[0] for r in rows))
conn.close()
"
```

Hold this list in context as **known clubs**.

## Step 3: Search for Comedy Clubs in City

Run at least 2 WebSearch queries to discover comedy clubs. Use varied phrasings to maximize coverage:

1. `comedy clubs in <city>` (or `comedy clubs in <city>, <state>` if helpful)
2. `best stand-up comedy venues <city>`
3. Optionally: `<city> comedy club schedule` — run if the first two queries have sparse results

From the results, extract a deduplicated list of comedy club names. Ignore:
- Theater chains with occasional comedy nights (not dedicated clubs)
- Bars that host amateur open mics
- Duplicates with slightly different capitalizations (normalize before deduplicating)

## Step 4: Fuzzy-Match Against Known Clubs

For each found club, compare against the **known clubs** list using these rules:

- **Exact match** (case-insensitive): mark as **Already in system**
- **Near match** (one is a substring of the other, or they differ only by "The", city name suffix, spacing, punctuation, or minor word differences): mark as **Already in system** with a note about the matched club name
- **No match**: mark as **Potentially new**

Be conservative — when uncertain, prefer marking as Already in system to avoid creating duplicate tasks.

## Step 5: Present Summary and Request Confirmation

Show the user a formatted summary:

```
## Comedy Clubs Found in <city>

### Already in system (skipped)
- Club A (matches: "Club A NYC")
- Club B

### Potentially new clubs
1. Club C — <website or source URL if found>
2. Club D — <website or source URL if found>
3. Club E — <website or source URL if found>
```

If **no new clubs** were found, say so clearly:

> All comedy clubs found in <city> are already in the system. Nothing to add.

Then stop — do not proceed to Step 6.

If **new clubs** were found, ask:

> Should I create scraper onboarding tasks for these clubs? You can:
> - **Confirm** to create tasks for all
> - **Remove** specific numbers (e.g., "remove 2, 3") to skip them
> - **Cancel** to stop without creating any tasks

Wait for the user's response before continuing.

## Step 6: Process User Confirmation

Apply any removals the user specified. Record the final confirmed list.

If the user cancelled or the confirmed list is empty, report:

> No tasks created.

Then stop.

## Step 7: Create Tasks via /create-task

For each confirmed new club, invoke the `/create-task` skill by reading and following:

```
Read file: /Users/mattgioe/Desktop/projects/laughtrack/.claude/skills/create-task/SKILL.md
```

Pass the following task description for each club (one at a time):

```
Add scraper for <club name>

Onboard <club name> as a new venue in the laughtrack scraper. This includes:
- Identifying the club's website and show listing page
- Determining the appropriate scraper type (e.g., Ticketmaster, SeatEngine, custom HTML)
- Implementing the scraper and adding the club to the DB
- Verifying scraped shows appear correctly

Club website: <URL if found, otherwise "TBD — research needed">
```

Use these metadata values for every club task:
- **domain**: scraper
- **task_type**: feature
- **assignee**: scraper
- **priority**: Low
- **complexity**: M

## Step 8: Report Final Results

After all tasks are created, show a summary:

```
## Results for <city>

**Tasks created**: N (for: Club C, Club D, Club E)
**Already in system**: M clubs skipped
**User removed**: K clubs skipped

| Task ID | Club |
|---------|------|
| #NNN    | Club C |
| #NNN    | Club D |
```

If zero tasks were created (all confirmed clubs were duplicates in `/create-task`), report that clearly.
