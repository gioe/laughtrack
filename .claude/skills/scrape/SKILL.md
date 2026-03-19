---
name: scrape
description: Run a scrape for all venues or a specific club. Usage: /scrape [all | <venue name> | id:<N> | types:<type1,type2>]
allowed-tools: Bash
---

# Scrape Skill

Accepts a natural-language prompt and runs the right scraper command.

## Arguments

Parse `ARGUMENTS` to determine intent:

| Pattern | Intent |
|---------|--------|
| (empty) or `all` | Scrape all configured venues |
| `id:<N>` or `id <N>` | Scrape a specific venue by database ID |
| `types:<t1,t2>` or `types <t1,t2>` | Scrape venues matching those scraper types |
| Anything else | Treat as a venue name — resolve and scrape |

---

## Step 1: Determine Intent

Read `ARGUMENTS` (the text after `/scrape`). Trim whitespace.

- If empty or equals `all` (case-insensitive) → go to **Run: All**.
- If starts with `id:` or `id ` → extract the integer N → go to **Run: By ID**.
- If starts with `types:` or `types ` → extract the comma-separated list → go to **Run: By Types**.
- Otherwise → treat as a venue name → go to **Step 2: Resolve Club Name**.

---

## Step 2: Resolve Club Name

The user provided a venue name. First list all clubs to resolve it:

```bash
cd apps/scraper && make list-clubs 2>&1
```

Scan the output for clubs whose name contains the user's input (case-insensitive).

- **Exactly one match** → note the club name. Go to **Run: By Name**.
- **Multiple matches** → ask the user to pick one:

  > I found multiple clubs matching "<input>":
  > - [ID] Club Name
  > - [ID] Club Name
  >
  > Which one did you mean? (Reply with the name or ID.)

  Wait for confirmation, then go to **Run: By Name** or **Run: By ID**.

- **No match** → inform the user and show the full list:

  > No clubs matched "<input>". Here are all available venues:
  > [list from make list-clubs]
  >
  > Try `/scrape <exact name>` or `/scrape id:<N>`.

  Stop.

---

## Run: All

```bash
cd apps/scraper && make scrape-all --no-print-directory 2>&1
```

After completion, go to **Step 3: Post-Run Summary**.

---

## Run: By Name

```bash
cd apps/scraper && make scrape-club CLUB="<resolved name>" --no-print-directory 2>&1
```

After completion, go to **Step 3: Post-Run Summary**.

---

## Run: By ID

```bash
cd apps/scraper && make scrape-club-id ID=<N> --no-print-directory 2>&1
```

After completion, go to **Step 3: Post-Run Summary**.

---

## Run: By Types

```bash
cd apps/scraper && make scrape-types TYPES="<t1,t2>" --no-print-directory 2>&1
```

After completion, go to **Step 3: Post-Run Summary**.

---

## Step 3: Post-Run Summary

After any scrape completes, print the performance summary:

```bash
cd apps/scraper && make scraper-status --no-print-directory 2>&1
```

Display the output to the user.
