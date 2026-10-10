# Event comedy eligibility contract

TASK-4153 supplies a pure classifier in `laughtrack.core.comedy_eligibility`, separate from the discovery `show_type` classifier. It does not construct or persist Shows, Comedians, or venues. TASK-4154 owns adapters, staging, cache validation and enforcement.

## Inputs and evidence

Adapters supply event-scoped `EventEvidence` with kind `comedy`, `music`, or `sports`, provenance `event_category`, `event_billing`, or `event_description`, and a nonblank supporting detail. These are normalized assertions about the event, not arbitrary keywords. Venue branding, performer biographies, existing comedian rows and broad words such as “open mic” are insufficient. Numeric platform category IDs must first be normalized with the correct platform/endpoint taxonomy. The classifier does not parse raw HTML or titles. Invalid or unsupported evidence forces review even when valid evidence is also present.

`PerformerObservation` carries a raw name and an optional existing ID, without creating an identity. `CanonicalPerson` is an explicit identity snapshot, not a persisted domain entity. Hidden roots or residual normalized name denials block identities. Parent chains resolve only to a visible non-denied root; aliases and their root deduplicate to one identity. Missing parents, cycles, conflicting duplicate IDs, mismatched names and ambiguous names remain identity conflicts. Name collisions are safe only when all matching paths resolve to the same root. Resolution caches live only for one call.

`DeniedName` supports raw names not present in the DB. Name normalization collapses whitespace and NBSP and lowercases consistently with ingestion deny matching. Missing lineups are `missing`; new/unverified or conflicted identities yield `partial`; a fully resolved lineup is `observed`, which does not mean verified comedy.

## Decision precedence

1. Invalid evidence → review.
2. Both explicit comedy and music/sports → review.
3. Explicit music/sports alone → reject, even on a comedy-only source or with recognized comedians. Identity conflicts remain in diagnostics.
4. Unresolved identity conflicts → review.
5. All resolved identities blocked → reject without affirmative event comedy; with comedy evidence, review unless every blocked identity qualifies for the structural-label exception.
6. A strict majority blocked → review with a warning, even with positive comedy evidence. Exactly half is not a majority.
7. Affirmative event comedy → accept.
8. A reviewed comedy-only policy → accept if no prior conflict/rejection applies. It must have reviewer, evidence and a valid timezone-aware review timestamp. A bare policy enum is insufficient trust.
9. Otherwise → review.

The structural exception requires a canonical snapshot or deny entry explicitly typed `troupe` or `show_label`, a matching observation structural kind, a nonblank reviewed structural proof, and affirmative event comedy evidence. Every blocked identity must qualify; a mixed lineup containing a blocked musician cannot use the exception. The default snapshot/deny kind is `person`, so changing only an observation label cannot override it. Explicit musician/sports block reason codes veto the exception even if a label type was supplied. Structural proof is retained in the output. These typed facts must come from reviewed evidence; do not infer them from names or generic block reasons.

Confidence numbers are deterministic rule strengths, not calibrated probabilities. `ComedyEligibilityDecision.to_dict()` is JSON-safe and retains source ID, policy and policy version, classifier version, sorted event evidence (including invalid assertions retained for operator review)/reason codes, resolved performer diagnostics, blocking counts and lineup coverage state. Decision consumers must compare source and policy versions before reuse; classifier-version changes also require re-evaluation. Gate mode deliberately does not affect classification: the dispatcher controls off, shadow and enforce behavior.

## Reviewed representative fixtures

The checked fixtures in `tests/integration/fixtures/comedy_eligibility_cases.json` are synthetic scenarios, not verified live listings or claims about current bookings.

| Scenario | Decision | Why |
| --- | --- | --- |
| Real stand-up showcase | accept | Event billing affirmatively specifies comedy; missing lineup remains unknown. |
| Comedy and music mixed bill | review | Both genres are explicit. |
| Harvelle’s-style live blues night | reject | Explicit music beats an unverified existing performer row. |
| Blocked alias with valid parent | accept | Parent clears alias block, deduplication counts one identity, and event category establishes comedy. |
| Second City-style troupe label | accept | Independently reviewed troupe label plus event-level sketch comedy evidence meets the narrow exception. |
| Recognized comedian at basketball event | reject | Performer identity does not turn a sporting event into comedy. |

Additional executable contracts cover missing lineups, raw deny entries, hidden/denied roots, missing/cyclic parents, ambiguous names, stale cache avoidance, strict-majority calculation, malformed evidence and source review metadata, structural spoofing and mixed blocked-person/label bills.
