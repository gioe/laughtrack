# Curation activation and recovery

TASK-4187 authorizes recovery of the failed rollout and moves unverified legacy
parent/host associations into pending review, preserving source evidence and negative
decisions. It does not approve identities or relationships. Production recovery must
pass the clone migration check and the disposable snapshot rehearsal below. TASK-4159 (historical shows) and TASK-3982 (lineup repair) remain separate.

## Current reconciliation baseline

Read-only production inventory on **2026-10-19**:

| Inventory                         |  Count |
| --------------------------------- | -----: |
| Comedians                         | 12,075 |
| Existing parent assignments       |    490 |
| Clubs                             |  3,067 |
| Podcasts                          | 11,353 |
| Source-specific host associations |    479 |
| Host candidate reviews            | 12,023 |
| Comedian deny-list entries        |  1,759 |
| Venue deny-list entries           |    114 |
| Unrestored podcast denials        |  2,002 |

The durable ledger exists, but `curation_club_keys(jsonb,jsonb)` is absent. These are
inventory counts, **not** approved or reconciled counts. The earlier failed club
migration and legacy graph preflights remain activation blockers; do not infer
production readiness from passing fixtures. Re-run the inventory and the bounded
plans immediately before cutover. Retain timestamped output in the rollout record.

## Deployment order and stop conditions

1. Pause scrapers, discovery/refresh jobs, event-review workers and notification
   delivery. Put admin mutation endpoints into maintenance mode. Snapshot the
   database and retain legacy denial/audit records. Record installed migrations,
   schema functions, row counts and publication revision. Inventory every active
   worker version, including scheduled/manual scripts.
2. Follow [CURATION-MIGRATION.md](CURATION-MIGRATION.md): run every listed legacy
   category in bounded read-only pages with an explicit destination/environment.
   Preserve each plan, snapshot digest, conflicts, source counts and cursor. Review
   all held rows; an exhausted cursor is not evidence that held rows were resolved.
   Apply only individually reviewed plans in the separately authorized rollout.
   Re-scan all categories to account for writes before earlier cursors.
3. Reconcile legacy clubs with reviewed venue evidence before enforcing admission.
   Preserve organizer/proxy routing flags; never approve all visible records.
   The authorized `20261016170000_stage_legacy_relationship_reviews` migration
   captures legacy parent/source rows as immutable observations, proposes unverified
   relationships and removes their live parent/accepted-host projections. Existing
   rejections become negative ledger decisions, including the old canonical root
   where an alias is quarantined; negative evidence wins across sources. No approvals
   are manufactured. Existing confirmed edges are retained. The parent and host
   preflights still run afterward. The staging migration alone temporarily suspends
   the comedian admission row trigger under an exclusive table lock, inside its
   transaction, to clear unverified parent FKs; it re-enables the trigger before commit.
   Do not disable guards manually or restore projections from an old snapshot.
4. Install schema in the order recorded in
   `lib/admin/curation/fixtures/migrations.json`: staging/event review, identity
   review, durable model, comedian intake, **show visibility foundation before
   club intake**, show intake, podcast intake, parent projection, host projection.
   The production failed club migration recovery is documented in
   [CURATION-SHOW-INTAKE.md](CURATION-SHOW-INTAKE.md). Inspect its failed migration
   record and verify rolled-back DDL before an explicitly authorized
   `prisma migrate resolve --rolled-back`; do not mark it applied or change its
   checksum. Stop if any schema or reconciliation precondition fails.
5. Deploy compatible web/API, scraper and review-worker versions while writes are
   paused. Verify the policy functions and statement/row triggers on every writer
   table. Missing policy is a hold/error, never a fallback to unconditional insert.
   Deploy notification rechecks before resuming delivery. Restore is pending or
   proposed, never approval; source enablement/visibility is a separate choice.
6. Run the gates below against disposable fixtures, then perform read-only checks
   on the destination. Canary one approved identity per type and one reviewed
   relationship per type only under the separate rollout's approval. Check receipts,
   public reads, revision invalidation and denial preservation. Resume writers in
   small batches, monitor conflicts/holds, then resume promotional delivery last.

## Writer and reader coverage

Paths below are relative to `apps/`. SQL guards are required even for old versions
that bypass a service-level check; database owners disabling triggers are outside
this compatibility contract.

| Surface                                                                 | Authoritative admission / projection                                                                                                                                                          |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Scraped comedian names, lineup writes, social/enrichment updates        | `scraper/src/laughtrack/core/entities/comedian/handler.py`; `curation_comedian_policy`, comedian/candidate/lineup triggers                                                                    |
| Venue discovery, provider identifiers, aliases and source configuration | `scraper/src/laughtrack/core/entities/club/curation.py`; club, alias, source and show guards                                                                                                  |
| All show scrapers including comedy-gate off mode                        | `scraper/src/laughtrack/core/entities/show/curation.py`, show handler; shared intake lock and occurrence/series policies                                                                      |
| Event Review worker and eligibility publication                         | `scraper/src/laughtrack/core/comedy_eligibility_gate.py`, eligibility/review stores and `comedy_admin_reviews.py`; same transaction/fence as publication                                      |
| Podcast discovery, feed refresh, episode insertion                      | `scraper/src/laughtrack/core/podcast_curation.py`; podcast/episode/deny-list guards                                                                                                           |
| Host candidate import, source-specific association upsert               | `web/lib/admin/curation/hostRelationships.ts`; host projection and candidate/association guards                                                                                               |
| Parent assignment and replacement                                       | `web/lib/admin/curation/parentRelationships.ts`; confirmed-parent guard, graph constraints and atomic replacement                                                                             |
| Admin Inbox decisions, retries and queued decisions                     | `web/lib/admin/curation/decisions.ts`; versioned request/decision transaction, real domain adapters, post-commit invalidation                                                                 |
| Legacy backfill and manual imports                                      | `web/bin/migrate-curation`, migration compatibility overlay; retained keys/negative history plus SQL guards                                                                                   |
| Public comedian, club, show and podcast reads                           | Shared identity/public predicates, `web/lib/data/podcast/publicWhere.ts`, `web/lib/data/show/publicationCache.ts`; accepted host projections only                                             |
| Show email/push and YouTube live push                                   | `scraper/src/laughtrack/core/services/notification/service.py`; current durable comedian policy and current alias membership at delivery, show/club visibility, fail closed on lookup failure |

Blocking prevents repeat admission using retained known keys: exact identities,
scoped venue names/places/provider IDs, occurrence IDs/explicit series, feed/provider
IDs. A wholly new identifier with no known connecting evidence cannot be deduced
as the same entity; it remains subject to normal review. Never replace identity
matching with fuzzy title/name substring blocking. Existing source configuration
can remain enabled while policy denies ingestion; restore does not enable a source.

## Gates and evidence

From the repository root:

```sh
cd apps/web
npm test -- lib/admin/curation/ app/api/admin/ lib/data/comedian/ lib/data/podcast/ lib/data/show/
npm run type-check
node bin/verify-curation-inbox.mjs
```

From the repository root, native PostgreSQL (requires `initdb` and `pg_ctl`):

```sh
apps/scraper/.venv/bin/python apps/web/bin/verify-curation-concurrency.py
```

This harness ignores all configured DSNs, creates a temporary UTF-8 cluster with
only a private Unix socket and always stops it. It verifies actual separate
connections waiting on the intake lock, denial after release, rollback on a lost
connection, retry, and the production promotion predicate. PGlite alone cannot
prove native multi-connection lock behavior.

From `apps/scraper` (set `PYTHONPATH` to the task checkout's absolute `src` path when
using a symlinked virtualenv):

```sh
PYTHONPATH="$PWD/src" .venv/bin/python -m pytest tests/integration/test_curation_comedian_intake.py tests/integration/test_curation_club_intake.py tests/integration/test_curation_show_intake.py tests/integration/test_curation_podcast_intake.py tests/core/services/notification/test_notification_service.py tests/core/services/notification/test_curation_delivery.py
```

`endToEnd.test.ts` installs all eleven migrations together, exercises the complete
publication graph and legacy writes, and verifies worker restart, partial-effect
rollback, idempotent replay, stale approval and policy outages. Domain suites add
changed-key rediscovery, cross-source occurrences, negative edges, cycles, atomic
replacement, conflicting host evidence and mixed-version migration/import tests.
Public-query/cache tests exercise the consumer predicates. The browser harness
uses the real Inbox components with a stateful test API at 1440px and 390px;
API/SQL contracts run separately. This is deliberately isolated from production.

## Operational reconciliation and metrics

Run `curation-health.sql` using a read-only connection **after** all schema steps.
Capture baseline and deltas per canary batch. It reports entity/edge states,
request outcomes and ages, stale projection mismatches, negative public projections,
and pending conflict holds. Source plans separately report imported/skipped/held;
those totals must reconcile against the inventory and every held row must have an
explicit disposition or an owner. Count source rows separately from canonical
entities: multiple source observations may intentionally collapse to one identity.

Stop activation for any projection mismatch, negative publication, unexpected
approval increase or lost denial. Investigate every failed request and pending
request older than five minutes. Treat conflicts as optimistic-concurrency signals:
track `conflict / (applied + conflict + failed)` over the last hour and compare with
the preceding baseline. A sudden increase or repeated conflicts for one target
requires inspection; do not auto-retry with a newer version. Policy-unavailable
logs are a stop condition for delivery/intake, even if worker processes are alive.

## Rollback preserving denials

Pause writers and delivery first. Roll back application binaries only to a version
known to tolerate the installed schema/guards. Leave the ledger, identity keys,
observations, negative decisions and enforcement triggers installed. Preserve
show publication revision and flush public caches. An old writer that is denied
may log errors or hold rows; that is preferable to removing enforcement.

Never down-migrate away denials, delete keys to unblock an import, bulk-enable
sources, restore visibility to roll back, or reset host/parent projections from a
legacy snapshot. If a prior application cannot operate with the guards, keep its
writes paused and roll forward a compatible fix. Correct individual decisions
through a versioned, attributed restore and fresh evidence review. A database
snapshot restore is not a routine rollback: it can lose newer manual denials and
requires a separately reviewed plan to replay those decisions before any writer
or promotional delivery resumes.

Delivery checks are made immediately before handing off to the external provider.
They cannot recall messages already handed off, nor make provider delivery atomic
with a later database decision. Pausing delivery is required during cutover.

## TASK-4187 recovery verification

`node bin/recover-curation-migration.mjs` is read-only by default. With `--apply`,
it resolves only the known club migration's zero-step PostgreSQL 42703 failure,
first checking that every club function rolled back. Unexpected failures or partial
DDL abort. It never marks a migration applied or changes checksums. CI runs this
same recovery against its ephemeral production clone, then runs normal
`prisma migrate deploy`; unrelated migration errors still fail CI.

The additive lookup performance migration runs before the visibility/club repair.
It uses indexed seed and denial lookups without changing admission semantics.
The source-identity storage tests isolate admission; the separate intake suites
continue exercising real enforcement and missing-policy failures. SQL CI installs
real policy functions omitted by Prisma's schema diff, and Python CI installs the
web dependencies needed by its cross-language contracts.

To rehearse the quarantine and benchmark using locally retained JSON snapshots:

```sh
apps/scraper/.venv/bin/python apps/web/bin/verify-curation-rollout.py \
  --policy-snapshot /private/tmp/task4187-policy-snapshot.json \
  --host-snapshot /private/tmp/task4184-host-snapshot.json
```

The harness ignores configured DSNs and uses a disposable native PostgreSQL server.
It verifies preserved parent evidence, negative host ledger coverage, unchanged
approval count, installed guards, and a 275-row bulk write under a 30-second timeout.
Snapshots contain production data and must not be committed or uploaded. The initial
rehearsal retained 490 parent observations and 12,530 host observations (including
negative propagation); 275 held updates took 0.47 seconds after optimization.
These timings are local evidence, not a production latency guarantee.

New intake and episode publication remain held until the corresponding identities
are approved. Pending source rows and removed alias projections are intentional
review outcomes, not permission to bypass the guards to restore ingestion volume.
