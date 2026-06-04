# Comedian Visible-Flag Consolidation

## Context

LaughTrack has two parallel mechanisms for keeping unwanted entities out of
discovery surfaces:

- **Clubs** use a `clubs.visible Boolean? @default(true)` soft-flag
  (`apps/web/prisma/schema.prisma:156`). Admin actions toggle it; data fetchers
  filter on it.
- **Comedians** use **hard-delete plus a `comedian_deny_list` table**
  (`apps/scraper/migrations/20260323_add_comedian_deny_list.sql`). Deleting a
  comedian cascades through ~10 child tables (favorites, lineup items, tags,
  podcast appearances, image assets, etc. — see `apps/web/prisma/schema.prisma`
  lines 224–272); the deny-list entry then blocks re-ingestion by name.

The deny-list is **purely name-keyed**, not id-keyed. The scraper looks up
membership via a normalized name match
(`apps/scraper/src/laughtrack/core/entities/comedian/handler.py:246` —
`re.sub(r"\s+", " ", name.replace("\xa0", " ")).strip().lower()`); the admin
API uses the equivalent Postgres expression
(`apps/web/app/api/admin/comedians/route.ts:512`).

Per the task description, the table holds **1,990 rows total**; **~1,642 have
no matching `comedians` row** — they are pre-emptive name blocks that never
corresponded to a real ingested comedian (extraction noise, OCR garbage,
"X & Y" composites, mis-extracted email addresses, etc.). Every row carries
audit metadata: `reason`, `added_by` (user email or `'audit_script'`),
`deleted_at`.

The admin API exposes the deny-list state as a computed boolean
`isBlocked: Boolean(denyListEntry)`
(`apps/web/app/api/admin/comedians/route.ts:284`). There is **no `isBlocked`
column** — it is derived per-request from a normalized-name lookup.

This document resolves three design questions before any code lands:

1. How to handle the ~1,642 orphan deny-list entries.
2. Whether to rename `isBlocked` → `isHidden` on the admin surface, and
   whether to keep `isBlocked` as a deprecated alias.
3. Forward migration and rollback plan for the 1,990 deny-list rows.

## Decision 1: Keep a residual `comedian_deny_list` for name-only orphans

Add `comedians.visible Boolean? @default(true)` with `@@index([visible])`,
mirroring the `clubs.visible` pattern. Migrate the ~348 deny-list rows whose
normalized name matches an existing `comedians.name` to `visible=false` on
that comedian row. **Leave the ~1,642 name-only orphan rows in
`comedian_deny_list`** as a pre-emptive ingest filter.

The scraper ingest filter
(`apps/scraper/src/laughtrack/core/entities/comedian/handler.py:545`
`_filter_denied_comedians`) becomes a two-stage check at ingest time:

1. Does a comedian row exist with this normalized name and
   `visible=false`? Skip.
2. Otherwise, does the normalized name appear in the residual
   `comedian_deny_list`? Skip.

### Why not auto-stub each orphan into `comedians`

Creating 1,642 hidden `Comedian` rows just to consolidate the data model adds
1,642 rows with no shows, no images, no podcasts, no real provenance. They
would also need a `source='deny_list_stub'` (or similar) sentinel to
distinguish them from real-but-hidden comedians for admin UI, search, and
analytics — which is just reintroducing a second flag through the back door.
Worse, several FK relations on `Comedian` use `onDelete: Cascade`: deleting a
stub later cascades through `FavoriteComedian`, `LineupItem`,
`TaggedComedian`, `ComedianImageAsset`, etc. There is no value in those
relations ever having stub rows on the parent side.

### Why not drop the orphan blocks entirely

The 1,642 orphans were added because the audit script and operators
identified them as names that should never become comedians. Dropping them
re-opens the door for the same extraction noise to be re-ingested on the next
scraper pass, undoing audit work. The orphans also carry `reason` and
`added_by` metadata; deleting them silently loses that audit trail. The
incremental cost of keeping a 1,642-row residual table is negligible.

### Why not key the deny-list on `comedian_id`

The reason the deny-list exists in its current form is to block names that
**have never been ingested**. A `comedian_id` FK cannot exist for an
un-ingested name. The two facilities serve different population subsets:
`comedians.visible=false` covers "we have ingested this person and decided to
hide them"; `comedian_deny_list` covers "this name must never be ingested in
the first place". They are complementary, not redundant.

## Decision 2: Rename `isBlocked` → `isHidden`, no alias, lockstep

Rename the admin serializer field from `isBlocked` to `isHidden`. **Do not
keep `isBlocked` as a deprecated alias.** Rename the admin actions from
`block`/`unblock` (`blocklist-add`/`blocklist-remove`) to `hide`/`unhide`.

### Why no alias is needed

The exploration for this ADR confirmed three facts:

- `isBlocked` is **not on the `/api/v1` public surface**. It appears only in
  `apps/web/app/api/admin/comedians/route.ts` — an auth-gated admin endpoint.
- `ios/Sources/LaughTrackAPIClient/openapi.json` contains **zero references**
  to either `isBlocked` or `isHidden` (verified by grep).
- The Swift client and tests under `ios/Sources/` and `ios/Tests/` reference
  neither field on any comedian-shaped object.

There is no cross-client lockstep cost to absorb. The "iOS regeneration" risk
in the original framing of this question is empty — there is nothing on the
iOS side to regenerate. An alias would protect zero callers.

### Effect on TASK-2642

The contingent task TASK-2642 ("Regenerate iOS LaughTrackAPIClient and update
call sites if `isBlocked` is renamed without an alias") should be closed as
`wont_do` at pickup. The iOS client does not consume `isBlocked` and does not
need to be regenerated for this rename. The task's own description authorizes
this disposition ("If the ADR chooses to keep the alias, mark this task
wont_do at pickup") — the present ADR reaches the same outcome by the inverse
route: the rename does not need an alias **because** there are no consumers,
which makes the iOS regen unnecessary either way.

### Effect on TASK-2640

TASK-2640 ("Rename comedian admin Blocked state to Hidden and switch admin
actions to `comedian.hide/unhide`") proceeds as filed: it is the
implementation of this decision on the admin surface.

## Decision 3: Migration plan and rollback

### Forward migration (one Prisma migration, two SQL steps)

1. **Schema** — add the column and index:

   ```prisma
   model Comedian {
     // ... existing fields ...
     visible Boolean? @default(true)

     @@index([visible])
   }
   ```

2. **Snapshot** — capture the entire current `comedian_deny_list` into an
   archive table the migration creates in the same transaction:

   ```sql
   CREATE TABLE comedian_deny_list_archive_pre_consolidation AS
     SELECT *, now() AS archived_at FROM comedian_deny_list;
   ```

   This snapshot is the rollback substrate and the audit trail. It is never
   read by application code; it exists so that the original `reason` /
   `added_by` / `deleted_at` for promoted-and-deleted rows can be
   reconstructed.

3. **Backfill** — for each deny-list row whose normalized name matches an
   existing comedian, set that comedian's `visible=false` and remove the
   deny-list row in a single statement. The UPDATE and DELETE share one
   CTE chain so that the DELETE can reference the same `matched` set the
   UPDATE consumed; splitting them into two statements would put `matched`
   out of scope for the DELETE and the migration would error mid-flight:

   ```sql
   WITH matched AS (
     SELECT c.id AS comedian_id, d.name AS deny_name
     FROM   comedian_deny_list d
     JOIN   comedians c
       ON lower(btrim(regexp_replace(replace(c.name, chr(160), ' '),
                                     '[[:space:]]+', ' ', 'g')))
        = lower(btrim(regexp_replace(replace(d.name, chr(160), ' '),
                                     '[[:space:]]+', ' ', 'g')))
   ),
   promoted AS (
     UPDATE comedians SET visible = false
     WHERE id IN (SELECT comedian_id FROM matched)
     RETURNING id
   )
   DELETE FROM comedian_deny_list
   WHERE name IN (SELECT deny_name FROM matched);
   ```

   After this statement the residual `comedian_deny_list` contains only
   orphan name-only entries (~1,642 expected; exact count to be verified
   against production at migration time).

   The normalized-name JOIN cannot use the existing index on
   `comedians.name` because both sides apply
   `lower(btrim(regexp_replace(...)))`. With ~50k comedians and ~1,990
   deny-list rows, expect a sequential expression-match. This is
   acceptable for a one-shot migration; if measured runtime is
   unreasonable, the implementation task can add a functional index on
   `comedians (lower(btrim(regexp_replace(name, ...))))` immediately
   before the backfill and drop it immediately after.

### Application changes that ship with the migration

- `apps/web/app/api/admin/comedians/route.ts`: derive `isHidden` from
  `comedians.visible=false` instead of `Boolean(denyListEntry)`.
  `denyListEntry` continues to be checked **in addition**, so admin UI still
  surfaces the orphan-name blocks correctly under whatever new admin surface
  TASK-2640 chooses for them.
- `apps/web/app/api/admin/deny-list/route.ts`: continues to manage the
  residual orphan table; admin docs note that the table is now
  orphan-only.
- `apps/scraper/src/laughtrack/core/entities/comedian/handler.py`:
  `_filter_denied_comedians` becomes the two-stage check described under
  Decision 1.
- Every public `/api/v1` data fetcher that lists or returns comedians adds a
  `where: { visible: true }` predicate, matching the existing `clubs.visible`
  pattern (`apps/web/lib/data/home/getFavoriteComedianShows.ts:14` is the
  canonical analog).
- Admin "delete comedian" actions are changed to `hide` by default. Hard
  delete remains available as an explicit override for spam/PII removal; it
  is no longer the path for ordinary "do not surface" actions.

### Rollback

The rollback is data-safe because step 2 snapshots the original deny-list
before step 3 mutates it:

1. **Application code**: standard `git revert` of the application PRs.
2. **Data**: restore the deny-list from the archive snapshot, then unhide
   only the comedians that were promoted from the deny-list at migration
   time. The `visible=true` update is scoped through the archive so that
   any comedians an admin operator legitimately hid after the migration
   (during the soak period) stay hidden through the rollback:

   ```sql
   TRUNCATE comedian_deny_list;
   INSERT INTO comedian_deny_list (name, reason, deleted_at, added_by)
     SELECT name, reason, deleted_at, added_by
     FROM   comedian_deny_list_archive_pre_consolidation;

   UPDATE comedians SET visible = true
   WHERE id IN (
     SELECT c.id
     FROM   comedians c
     JOIN   comedian_deny_list_archive_pre_consolidation a
       ON lower(btrim(regexp_replace(replace(c.name, chr(160), ' '),
                                     '[[:space:]]+', ' ', 'g')))
        = lower(btrim(regexp_replace(replace(a.name, chr(160), ' '),
                                     '[[:space:]]+', ' ', 'g')))
   );
   ```

3. **Schema**: `ALTER TABLE comedians DROP COLUMN visible;`. No application
   code depends on the column at this point because step 1 already reverted
   it.

The archive table is retained indefinitely as an audit artifact; a follow-up
chore task can drop it once the consolidation has soaked in production for an
agreed period (e.g., one quarter).

## Cross-client lockstep summary

| Surface | Touched by this consolidation? | Action |
| --- | --- | --- |
| `apps/web` admin API | Yes — serializer rename, action rename | In TASK-2640 |
| `apps/web` `/api/v1` public read paths | Yes — add `visible: true` filter to comedian queries | In TASK-2640 (or a sibling task) |
| `apps/scraper` ingest filter | Yes — two-stage check | In TASK-2640 |
| `ios/Sources/LaughTrackAPIClient` (OpenAPI client) | **No** — no `isBlocked`/`isHidden` in `openapi.json` or Swift today | TASK-2642 → `wont_do` |
| `ios/` Swift call sites | **No** — no `.isBlocked` references | TASK-2642 → `wont_do` |

The cross-client parity rule in the repo `CLAUDE.md` is observed: the rename
is being made deliberately on one client (web admin), the other client (iOS)
is checked and explicitly noted as not requiring a mirror change, with the
reason recorded here.

## Reversibility summary

| Concern | Reversibility |
| --- | --- |
| Schema (add `comedians.visible`) | Trivially droppable; nullable with a default. |
| Backfilled `visible=false` rows | Reversible from the archive snapshot. |
| Deny-list rows promoted into `comedians.visible=false` | Reversible from the archive snapshot. |
| Orphan name-only deny-list rows | Untouched by migration; reversibility N/A. |
| `isBlocked` → `isHidden` rename | Reversible by git revert; no consumers depend on either name. |
| Admin `block`/`unblock` → `hide`/`unhide` action rename | Reversible by git revert; admin operators are the only callers. |

## Open items deliberately out of scope

- **Soft-delete for the cascading child tables** (`FavoriteComedian`,
  `LineupItem`, etc.) when a comedian is hidden. This ADR treats `visible`
  as a read-time filter on the parent only; child rows remain intact so
  unhide is a no-op restore. If a future requirement demands "user
  favorited comedian X who is now hidden", the existing `where: { visible:
  true }` filter on the favorites query already handles UI suppression
  without touching `FavoriteComedian` rows.
- **A dedicated admin surface for the residual orphan deny-list.** The
  existing admin deny-list endpoints
  (`apps/web/app/api/admin/deny-list/route.ts`) continue to manage it
  unchanged; UI work, if any, belongs to a separate task.
- **Backfilling `Reason` / `added_by` onto `comedians.visible=false`
  rows.** The audit metadata moves into the archive snapshot rather than
  into the `comedians` table to avoid widening that table. If reason-on-
  comedian-row becomes important later, it can be added in a focused
  follow-up migration without revisiting this ADR's core decisions.
