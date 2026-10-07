# TASK-4132 — Remaining Big Pine inventory

Status: cleanup applied and independently verified; normal live scrape and recovery regressions passed.

On October 7, 2026, the scraper's SeatEngine client fetched all 53 stored native
show details successfully and the current venue553 feed (16 entries).
The native list and detail responses are in native.json; inventory.json contains
only public show identity fields. Decisions for every remaining row appear in
decisions.json. Private database and dependent-row snapshots stay outside Git.

The reviewed disposition is **36 remove, 16 retain, 1 hold**:

| Product evidence | Remove count |
| --- | ---: |
| Submission inventory, including digital submission7773673/native390223 | 6 |
| Digital Download inventory | 14 |
| Digital/EPK/social-media review service inventory | 7 |
| Virtual Consultation inventory | 5 |
| Camp passes explicitly admitting workshops/panels | 3 |
| Networking game with revival-life add-on | 1 |

Each removal matches a native show ID, venue553, URL, and UTC start instant.
Classification uses explicit inventory/add-on evidence, not broad title words.
For example, submission390223 sells Digital Submission inventory and a written
video/bio-review add-on. Networking game340141 sells a revival life that restores
an eliminated player to competition. These are not performance tickets.

The 16 retained rows have matching native identities and dates and performance
or festival-admission inventory. This includes the Big Pine festival pass363358,
Big Tomato festival361183, and all reviewed named comedy performances. Festival
visibility, source360, platform sources3126/7146 and source targets1/2 must remain
unchanged. This task does not convert the festival into a producer or change the
existing title exclusions.

**Hold522192/native356284:** the database date is May10 at16:00Z, whereas the
fresh native date is May3 at16:00Z. Its workshop/panel inventory confirms an
education product, but the occurrence-date discrepancy remains unresolved.
The cleanup excludes this row and preserves it unchanged; no deletion or date
repair is inferred from its title or from unavailable historical pages.

The original TASK-4111 19-ID deletion list remains frozen. Its old private backup
is not a current before-image and must not be restored over newer writes.

Native endpoints, verified against the client implementation:

- https://services.seatengine.com/api/v1/venues/553/shows
- https://services.seatengine.com/api/v1/venues/553/shows/390223 (submission example)

The cleanup used fresh locked snapshots, exact row counts/hashes, private
backups before mutation, and seven-table dependency checks. It deleted exactly
36 shows, 38 tickets, 6 lineup items, and 72 show tags. Saved shows, notifications,
and discovery snapshots were empty for this cohort. All 1,146 club click records
survived: 607 deleted-show references became null, 497 previously detached clicks
remained unchanged, and 42 retained-show references remained intact.

Independent checks after rollback, committed apply, and the normal live scrape
appear in rollback-verification.json, apply-verification.json, and
live-verification.json. The latter two have identical state hashes. The public
plan-summary.json contains counts and hashes; the complete plan and row images
remain private because they contain click/user identifiers.

The normal run, scraper:2026-10-07T19:43:18.765043, fetched 16 native entries over
HTTP 200 and the existing anchored title filters excluded all 16 products. It
inserted and updated zero shows. Diagnostics retained items_before_filter=16,
so the all-filtered response did not become a clean-empty reconciliation signal.
All 17 preserved show IDs and dependencies were unchanged after that run.
A subsequent cleanup dry run reported already_applied=true without mutation.
See live-scrape.json for the run metrics.

Validation: 21 PostgreSQL regression cases passed against isolated temporary
tables, including exact cleanup, private backup failure, all seven dependency
relations, full restore, retained-row/source/target/click drift, altered schemas,
malformed plans, and recovery checksums. Seven SeatEngine inventory tests passed,
including this fresh native feed and all 16 retained admissions. The complete
configured scraper test gate passed for the implementation commit.

## Running and recovering

From apps/scraper, use the scraper virtual environment and worktree src on
PYTHONPATH. The CLI requires an explicit private reviewed plan. Production
artifacts for this execution are /private/tmp/task4132-reviewed-plan.json,
/private/tmp/task4132-recovery.json (before mutation), and
/private/tmp/task4132-recovery.json.after.json (complete recovery image).
Do not put those files in Git or publish their row data.

```sh
.venv/bin/python3 scripts/core/cleanup_remaining_big_pine_inventory.py \
  --plan /private/tmp/task4132-reviewed-plan.json --dry-run
```

A committed apply requires --apply and a new private --backup path. Recovery
uses --restore with the complete .after.json image and the same reviewed plan;
it restores shows before cascading dependencies and reattaches existing click
rows. Both directions reject schema or protected-state drift. Recovery was
exercised in PostgreSQL tests; production was not restored after cleanup.
Never reuse the TASK-4111 backup over these newer writes.
