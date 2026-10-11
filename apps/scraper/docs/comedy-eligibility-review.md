# Event eligibility review

Review individual staged events without changing a venue's visibility, source
policy, comedian visibility or deny-list entries. A source remains mixed even
when an operator approves one comedy performance and rejects its music nights.
The optional model remains disabled by default and is not required for review.

Run from `apps/scraper`:

```sh
.venv/bin/python -m scripts.core.review_comedy_eligibility list --source-id 7 --limit 25
.venv/bin/python -m scripts.core.review_comedy_eligibility inspect 42
.venv/bin/python -m scripts.core.review_comedy_eligibility preview --candidate-id 42 --action approve --actor operator-name --reason 'Event page explicitly bills stand-up comedy'
.venv/bin/python -m scripts.core.review_comedy_eligibility apply --preview-id PREVIEW_ID --token-digest DIGEST --actor operator-name --idempotency-key UNIQUE_OPERATION_KEY
```

`list` and `inspect` are read-only. Filters include source, venue, machine
decision, review state and lineup coverage (`missing`, `partial`, `observed`).
Carry both `next_after_id` and `ceiling_id` into the next page. Candidate IDs give
stable ordering; newly staged candidates beyond the ceiling wait for a new scan.
Filter membership can change as new observations arrive.

Inspection exposes event evidence, performer block reasons, resolved canonical
IDs, coverage, source information and observation/review history. Observations
record the actual revision seen on every delivery, even when a delivery reuses an
older identical decision. Legacy candidates with no recorded current observation
need a fresh scrape before review; the tool does not guess from timestamps.

`preview` stores an expiring plan and prints `operation: PLAN`; it does not apply
reviews or publish shows. Repeat `--candidate-id` for an explicitly bounded bulk
operation. Every action requires an attributed operator and nonempty reason.
Inspect the exact IDs and snapshot tokens before applying. Apply validates the
entire batch before mutation, including current source policy, event observation,
previous review version and live parent/deny state. Changes or expiry require a
new preview. Retry a successful apply with the same idempotency key and preview
to retrieve the same result; reusing a key for different content fails.

Approvals are consumed on the next normal scrape through the usual ShowHandler
validation, deduplication and publication fence. The CLI does not reconstruct or
publish incomplete historic payloads. Repeated approved observations retain the
same human decision identity and use normal public-show upserts. A human reject
or defer withholds that event in both shadow and enforce mode. Mode off preserves
legacy ingestion and bypasses event reviews; inspection still preserves history.
These actions do not delete previously published inventory.

A human decision takes precedence over optional model output. If event payload,
source policy, deterministic classifier or relevant canonical/deny identity state
changes, the previous human decision becomes stale and the event is held for
explicit re-review. Unchanged deliveries keep their review even as observation
generations increase. Pending publications are fenced against intervening human
actions. Source locks and candidate review versions also protect the exceptional
shadow staging-failure path; unknown review authority withholds publication.

Review actions, operation records and observed revision history are immutable.
An operator can change an earlier judgment only by creating another attributed
preview/action. Event approval does not grant blocked names permission to become
public comedians; normal downstream identity and deny filters still apply.
