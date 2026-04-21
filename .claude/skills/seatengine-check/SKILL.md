# SeatEngine Check

Check the health of a single SeatEngine venue by its venue ID or club name/ID.

## Usage

```
/seatengine-check 90
/seatengine-check Iplay America
```

## Arguments

- A SeatEngine venue ID (numeric), OR
- A club name or club DB ID — resolved to a SeatEngine venue ID via DB lookup

## Step 1: Resolve the SeatEngine Venue ID

If the argument is numeric and could be either a SeatEngine venue ID or a club DB ID,
check both. SeatEngine IDs are typically 1-700; club IDs can be higher.

If the argument is a name, look it up:

```bash
cd apps/scraper && .venv/bin/python3 -c "
import os, json
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
cur.execute(\"SELECT id, name, seatengine_id, scraper FROM clubs WHERE LOWER(name) LIKE LOWER(%s)\", ('%<name>%',))
for row in cur.fetchall():
    print(f'  club_id={row[0]}  name={row[1]}  seatengine_id={row[2]}  scraper={row[3]}')
conn.close()
"
```

If the club doesn't have `scraper='seatengine'` or has no `seatengine_id`, inform the
user and stop.

## Step 2: Run the Check

```bash
cd apps/scraper && make seatengine-check ID=<seatengine_venue_id>
```

The command outputs a formatted report and exits with:
- **0** = healthy (venue exists, has shows)
- **2** = dead or empty (404, redirect, or 0 shows)

## Step 3: Interpret Results and Recommend Action

Based on the output:

| Verdict | Recommendation |
|---------|---------------|
| **HEALTHY** | Venue is working. No action needed. |
| **EMPTY** | Venue exists on SeatEngine but has 0 shows. Check the venue's website — may be genuinely between shows, or may have moved to a different ticketing platform. Suggest `/adopt-scraper <name>` to investigate. |
| **DEAD** | SeatEngine API returns 404. The venue is no longer on SeatEngine. Suggest `/hide-club <id>` if the venue is confirmed closed, or `/adopt-scraper <name>` if the venue may have moved platforms. |

## Step 4: Report

```
SeatEngine Check: <Club Name> (SE ID: <venue_id>)
Status: <HEALTHY|EMPTY|DEAD>
Shows: <count>
Action: <recommendation>
```
