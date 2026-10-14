# Durable intake curation

This additive substrate does not activate intake enforcement, backfill decisions, or change existing visibility. TASK-4177 supplies the transactional service, TASK-4178 migrates legacy decisions, and subsequent entity/relationship adapters adopt this contract. Existing ingestion and review flags remain authoritative until those cutovers.

## Identity and matching

`curation_entities` is a durable identity for a candidate or existing entity, not its public record. Kind is comedian, club, show, or podcast. Optional typed public-record links use SET NULL on deletion. Decisions and keys remain. Recreated public records must resolve these keys before insertion and bind to the existing identity; creating a new UUID is not permission to ignore a block.

Identity scope `entity` identifies one subject. `name` is an explicit exact-value rejection rule, not positive identity proof. `series` identifies an explicitly selected show series, never all events with a similar title. Name/series rules cannot be approved, bound to public records, or used as relationship endpoints. Restore removes the negative disposition by returning to pending.

Identity keys are unique by (entity kind, namespace, scope, value). Namespace identifies the provider and contract version, e.g. `ticketmaster:v1`; scope identifies its account/venue partition or an explicit `global`. External IDs are opaque and case sensitive. A show occurrence uses a stable provider event ID; title, mutable URL, and date alone are insufficient. Feed URL normalization must be a documented provider contract: do not discard query parameters or infer redirect equivalence generically. Legacy IDs must include the original table/environment namespace. Multiple verified keys may resolve to the same identity.

Exact-name rules use `exact-name:v1` and `normalizeExactNameV1` in `lib/admin/curation/contracts.ts`: NFC, collapse Unicode White_Space to ASCII space, trim ASCII spaces, locale-independent lowercase, NFC again. Preserve punctuation and accents; do not remove words, use substring containment, or fuzzy-match. Python adapters must implement this exact whitespace set (not Python's broader str.isspace) and verify parity before adoption. Database checks enforce key shape; adapters must call the normalizer. Such rules target known invalid intake values (e.g. Special Guests!), not unverified namesakes. Ambiguous venue names or performer collisions remain pending; context/evidence must resolve them.

Keys are append-only. A discovered incorrect mapping or physical merge requires an explicit reviewed reconciliation strategy in the service; never silently move a key and thereby lose its negative decisions. `alias_of` retains separate identities and does not perform a destructive merge. Conflicting decisions on aliases/keys must be surfaced rather than selecting whichever observation arrived last.

## Independent state machines

Entity disposition: pending → approved (approve); pending/approved → blocked (block); blocked → pending (restore).

Relationship disposition: proposed → confirmed (confirm); proposed → rejected (reject); confirmed → severed (sever); rejected/severed → proposed (restore).

Public visibility is a separate existing domain concern. Approval does not implicitly publish; hiding does not erase curation. Legacy comedian visibility suppression and club organizer-routing behavior need explicit adapter mapping, not a shared hidden=blocked assumption.

Processing state belongs to `curation_requests`: pending → applied/conflict/failed/canceled. Terminal requests are immutable; retry transport delivery with the same ID, and submit a new request after a terminal failure. A pending request is not a decision. Requests carry immutable target/action/expected version/actor/reason. Applied results must refer to the matching decision. TASK-4177 must atomically insert the decision and mark the request applied, with authorization and idempotency checks.

## History, transactions and graph rules

Observations are append-only source evidence, deduplicated per target/source/source-key/fingerprint. They never approve or restore anything. Decisions are append-only with actor, reason, evidence, before/after state and resulting version. Manual negative decisions have no TTL. Rediscovery, source changes, public-record deletion, and new evidence cannot remove them. Explicit restore reopens review; it never auto-approves a subject or restores its relationships.

Append a decision to apply a transition. The AFTER INSERT trigger locks the target, requires version=current+1 and exact before-state, validates the transition, and updates the projection atomically. AFTER is essential: ON CONFLICT DO NOTHING must not apply a skipped decision. Stale versions raise SQLSTATE 40001; invalid transitions/graph constraints raise 23514; uniqueness raises 23505. Re-read stale items for review rather than blindly retrying an old approval. Direct state updates are rejected; trigger-depth checks are integrity guards, not a substitute for service authorization.

Relationship identity is (kind, source identity, target identity), independent of discovery source. Alias edges point child → parent, both comedians; host/cohost edges point comedian → podcast. Multiple hosts are allowed. An alias child has at most one confirmed parent. Self-links and cycles are rejected. Confirmation writes the singleton graph lock before walking ancestors, serializing concurrent graph confirmations; under repeatable read conflicting writes abort rather than use stale graph snapshots. Services must handle serialization/deadlock retries transactionally. PGlite tests verify actual SQL constraints and cycle rejection, not multi-connection concurrency.

New tables use restrictive history FKs and typed composite endpoints. Keep SQL CHECKs, triggers, and the partial one-parent index when generating future migrations: Prisma cannot express them all. No production migration is applied by this task. The existing domain records are untouched; legacy decision backfill must retain actor/evidence and avoid manufacturing approvals for old unvalidated records.
