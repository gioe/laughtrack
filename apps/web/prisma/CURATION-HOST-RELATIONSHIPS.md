# Podcast host relationship curation

The decision key is the canonical comedian identity, podcast identity and role
(`host_of` or `cohost_of`). Discovery source is observation provenance, never a
separate approval key. Multiple hosts/cohosts are supported. Confirm requires an
independently approved and validated visible comedian, an approved podcast and
source evidence. It never approves either endpoint.

Reject and sever persist on the pair across source and confirmed-alias retries.
Restore only reopens the pair for review. Entity restoration never restores a
negative relationship. Confirmed pairs have one `curation` association projection;
other source rows remain as `superseded` observations. Candidates share the pair's
accepted/rejected/pending state and decision actor/time. Original source payloads
are retained in immutable observations before any projection coercion.

The SQL boundary applies to Python discovery, Prisma, imports and maintenance
writes. Claimed accepted/rejected statuses cannot make a decision. Host endpoint,
role and source edits are refused once bound; insert a new observation instead.
The curation projection cannot be deleted; sever its relationship. Unbound podcast
candidates stay pending, with evidence retained until they can be bound.

## Admin operations

`GET /api/admin/curation/hosts?podcastId=...` returns relationships, all observations,
decisions and identity reconciliations. POST takes `{operation,input}`:

- `propose`: comedianId, podcastId, role (`host`/`cohost`), source, sourceKey,
  evidence object and reason. Returns relationshipId without changing its decision.
- `preview` / `submit`: the shared command shape, including requestId, typed
  relationship target, expectedVersion, action and reason. Actions are confirm,
  reject, sever and restore. Replays are idempotent; stale versions fail closed.
- `previewReconciliation`: `{id}` returns a token, both existing decisions and effects.
- `reconcile`: `{id,requestId,token,reason}` acknowledges the exact previewed states.
  This is replay-safe and retains an immutable actor/reason/state receipt.

The generic `/api/admin/curation` also supports host/cohost commands. The old
ownership endpoint delegates the new operation/input shape to this same service.
Its legacy bulk list mutation is refused: it must not erase other valid hosts or
reject unselected candidates implicitly. Explicit podcast block/restore remains a
separate entity operation. Manual RSS imports stage host evidence and return
`hostReviewRequired`; they do not accept a host. Legacy per-source comedian-tab and
Review Inbox mutations/undo are read-only. The unified relationship controls and
replacement of these legacy source views are the separately scoped TASK-4185.

## Canonical identity changes

Bindings retain the originally observed comedian and the relationship identity.
Parent changes preview affected host holds, including conflicting decision states.
After the parent projection changes, affected source identities are rebound to a
proposed/current canonical pair and a reconciliation hold records both old and new
relationships. Neither decision is rewritten or merged, even if one is confirmed
and the other rejected. A hold suppresses affected attribution until explicitly
reviewed. Source retries cannot resolve it.

Reconciliation acknowledges both states without changing either. A rejected new
pair still needs restore then confirm. A confirmed eligible pair can publish again
once all its holds are resolved. The preview identifies the affected states and
hold-release effect; stale decision versions invalidate it. Parent edits and host
writes share the same SQL intake lock. Parent preview tokens include affected host
versions. Publication revision changes invalidate public caches; host severing
leaves other hosts, episodes, appearances, favorites and both endpoint entities intact.

## Rollout

Do not deploy the migration until legacy decisions are reconciled across sources.
The preflight refuses every accepted/rejected source row without a matching
confirmed/negative canonical-role ledger decision. Conflicting legacy source states
require explicit review, preserved observations and normalized source projections;
never automatically approve all accepted rows or discard rejected rows. The earlier
failed club migration and parent-assignment reconciliation also remain prerequisites;
see CURATION-SHOW-INTAKE.md and CURATION-PARENT-RELATIONSHIPS.md.

Run the migration's initial read-only preflight query before `prisma migrate deploy`
(replace its exception with a count for reporting). If it fails, stop before deploy
so Prisma does not register another failed migration. The migration bulk-stages
source evidence and pending identities; only already reviewed pairs are projected.
No production data or schema changes were performed by TASK-4184.

The 2026-10-17 read-only snapshot contained 479 associations and 12,023 candidates,
with 12,075 comedian and 11,353 podcast identity rows. Local validation uses:
`CURATION_HOST_SNAPSHOT=/private/tmp/snapshot.json npm test -- lib/admin/curation/hostRelationships.test.ts`.
The fixture first verifies refusal of unreconciled decisions, then simulates explicit
reopening only in a disposable clone while retaining original states in evidence.
It verifies source-row preservation and no inferred confirmations. This is a test
scenario, not a production reconciliation script. CI uses synthetic decision cases.

Rollback should disable relationship decision entry points and retain the ledger,
observations, holds and projection guards. Do not drop durable negatives or restore
source-status writes. Resolve a failed deployment transaction using the established
Prisma recovery procedure, then deploy a corrective migration.
