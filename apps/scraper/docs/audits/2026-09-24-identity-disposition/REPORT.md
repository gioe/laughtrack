# TASK-4043: September 24 identity disposition

This is an operational production repair, not a schema migration. Prevention is
already merged in TASK-4040, TASK-4041/4062, and TASK-4042 (base b76db681e).

## Reviewed scope

`decisions.json` records all 174 identities, exact identity guards, original
visibility/block/parent fields, before counts, and individual dispositions.
`shows.jsonl` records all 2,023 candidate lineup associations, show identity
fields, original cast UUIDs, and per-show disposition. These are associations,
not distinct-show counts. Source descriptions are retained for attribution cases.
`attributions.json` records 24 per-show mappings and source evidence.

- Suppress 162 false identities using visible=false and TASK-4043 block metadata.
- Correct three verified single-performer names in place: Success Jr, Rob Anderson,
  Michael McIntyre. Each original UUID already equals the canonical name UUID;
  suppressing that UUID would incorrectly block the real performer. Every attached
  show supports the same performer. No parent or broad alias is created.
- Detach three incorrect parent mappings: Jackie Fabulous with Adyn Hamann,
  Ry Daddy ft: Daniel Simonsen, and The Benson Movie Interruption. Preserve Ryan
  Dacalos's existing direct links on all 49 Ry Daddy shows; add Doug Benson only
  to reviewed show 447441. The Benson host evidence is the official series
  [venue listing](https://calendar.dynastytypewriter.com/shows/the-benson-movie-interruption-02-jun).
- Keep the remaining 75 reviewed parent relationships on decorated performer
  aliases. Their false display names are hidden; real canonical performers and
  their associations survive. Alfred Robles and La Chupitos receive missing
  direct canonical links on five reviewed shows.
- Retain Emily Winter and Blue Man Group. Retain the three HTML-encoded collective
  names (Raynes/David Wimbish, Emily Lehr/Foxglove Fellows, Father Frank/Under The
  Canopy): an HTML entity alone does not establish a false identity. Their genre
  eligibility is not inferred from their names.
- Preserve all four already-hidden identities, including both School Girls
  variants, The Qs, and more!. Never unsuppress an identity.

The original 23-record contamination cohort included legitimate Blue Man Group.
The other 22 represent event titles, ballets/orchestras, workshops and musicals,
not stand-up identities. Crowdwork prose fragments and musicians lifted from
song descriptions are suppressed as erroneous attributions, not on name shape.
The expanded title cohort includes show dates, series, classes and tour subtitles.

## Per-show identity decisions

A title does not establish a global alias. Jasmine's four shows have three different
hosts; Stella's four shows have four distinct bills. Only explicit source-billed
performers are added to each individual show. Existing real cast is retained.
No blanket merge or transfer occurs. David/Dave Razowsky equivalence is unverified;
class instructors are not automatically treated as performing. Pablo Zuniga,
GRACE & MAMRIE, and Mouth Stuff receive no guessed canonical identities. The
suppression preserves those events and existing real cast for later enrichment.

## Execution and rollback

From apps/scraper in this worktree, with its source on PYTHONPATH:

```sh
PYTHONPATH="$PWD/src:$PWD" .venv/bin/python3 docs/audits/2026-09-24-identity-disposition/repair.py --receipt /tmp/task4043-dry-run.json
# Commit only after reviewing the successful dry run:
PYTHONPATH="$PWD/src:$PWD" .venv/bin/python3 docs/audits/2026-09-24-identity-disposition/repair.py --apply --receipt /tmp/task4043-applied.json
```

The script uses a repeatable-read transaction, row locks, exact ID/UUID/name/state
and show guards, explicit source-supported names, deny-list/canonical collision
checks, and an advisory lock. It aborts on drift or ambiguity. The default rolls
back. Both modes exercise rollback under a savepoint and compare original state.
Sequence numbers consumed by rolled-back inserts can leave harmless gaps.

It never deletes shows, favorites, existing lineups, or comedian rows. Immediate
verification compares every protected show and lineup row and all candidate
favorites before and after. New canonical inserts preserve source spelling and
use the production UUID utility. Repair receipts contain exact inserted lineup
IDs and before/after identity state. No profile identifiers are exported.

To reverse a committed repair, pass its receipt to `--rollback`, a fresh
`--receipt` output path, and optionally `--apply`. Default rollback mode is also
a dry run. Identity or inserted-lineup drift aborts the whole rollback for manual
review; it never removes a later replacement lineup by show/comedian alone.
Valid newly created canonical records remain, avoiding cascading deletion of
later enrichment. If the process dies between commit and receipt finalization,
inspect the prepared receipt and exact production state before doing anything;
a false committed flag alone does not establish that the database rolled back.

## Verification

Pending execution results and subsequent live scrape verification are recorded
in the accompanying receipts and verification artifact. Later normal scrapes may
remove old hidden garbage associations through the normal lineup reconciliation;
they must preserve legitimate events/performers and must not recreate visible
false identities. Historical shows are outside future-only scrape windows, so
immediate guarded preservation and source review cover those associations.
