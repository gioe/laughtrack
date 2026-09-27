# Source-specific repair handoff

Created after semantic backlog review, title duplicate checks, explicit scope
selection, and a successful batch-import dry run. Each task has two executable
regression-test contracts and a live-source/persistence verification criterion.
The named tests are implementation targets, not tests that already exist or passed.

| Task | Priority | Deliverable | Snapshot evidence |
| --- | --- | --- | --- |
| TASK-4086 | High | Recover Grisly Pear event metadata from current calendar links | 35 date-matched shows, 145 memberships; only one stored URL currently emitted |
| TASK-4087 | Medium | Recover explicitly billed Gotham performers from source descriptions | Three shows, six memberships |
| TASK-4088 | Medium | Recover Gotham lineups announced only on dated event posters | Six shows, 29 memberships |

## TASK-4086 — Grisly Pear

Scope: src/laughtrack/scrapers/implementations/venues/grisly_pear/** and matching
tests/scrapers/implementations/venues/grisly_pear/** beneath apps/scraper.

- test_pipeline_smoke.py::test_current_calendar_detail_identity must use the
  captured old/current calendar formats, authoritative detail dates/venues, and
  the October 8 → October 1 redirect mismatch. Preserve existing show identity
  without creating duplicate performances.
- test_pipeline_smoke.py::test_explicit_detail_lineups must cover actual JSON-LD
  and Featuring names, deduplication, Special Guest exclusion, genuinely empty
  events, and detail failures that cannot authorize stale deletion.
- Verify both venues through the actual scheduled stack before safely refreshing
  source-matched existing performances. Never create people from show titles.

Context 708 points to grisly/analysis.json, the real excerpts, current calendar
anchors, and unresolved shows 6331162/6395741. Recovery count is a dated baseline,
not a future fixed success threshold.

## TASK-4087 — Gotham description billing

Scope: src/laughtrack/core/clients/gotham/models/models.py, venue gotham/**, and
matching venue tests beneath apps/scraper.

- test_feed_models.py::test_explicit_billed_description_lineup covers Laugh for
  Sight featuring/host text and Mixtape hosted-by text, excluding historical
  has-featured lists, biography credits, and music credits.
- test_feed_models.py::test_unannounced_description_remains_empty preserves
  unknown lineups, source descriptions, ticket/date identity, and existing
  performer validation/suppression.
- Revalidate current source billing and persisted memberships on a fresh scrape.

Context 709 points to the matched feed, transformation reproduction, and the
three exact example IDs. Resolve Shaun Eli's identity before creating a record.

## TASK-4088 — Gotham poster text

Same Gotham model/venue/test scope as TASK-4087.

- test_feed_models.py::test_verified_poster_lineup uses retained
  poster-5509344.png and only printed names matched to event date, time, and room.
  Reuse the project's image-text extraction path where suitable.
- test_feed_models.py::test_unverified_poster_lineup_rejected covers retained
  logo-only poster-6337176.png, stale/conflicting poster-4400553.png, TBA, branding,
  mismatched times, and bounded repeated-asset fetching/extraction.
- Verify live printed announcements; preserve unknown when source identity is
  ambiguous. Never identify performers by faces.

Context 710 preserves the poster evidence and Brian Fischler conflict. Existing
identity and public-tag gates remain authoritative even when a name is printed.

## Existing work and dependency decision

UP per-instance room associations and repeated ticket URLs were attached as
context 711 to existing TASK-4065. Its investigation must verify dates and venues
before correcting records. Ambiguous class rosters and alumni are not cast.
No additional UP lineup task is justified by this evidence.

No hard dependency was added: the three repairs have independently demonstrable
inputs and acceptance conditions. The two Gotham tasks share a model file and
must reconcile edits when landing, but poster extraction does not require the
description parser to ship first. No existing open task supplies a missing
prerequisite established by this investigation.

Run each regression target from apps/scraper with .venv/bin/python3 -m pytest
followed by its tests/scrapers/implementations/venues/... node ID and -q. Use the
task worktree's src on PYTHONPATH when its virtualenv is symlinked. Full exact
commands, scope, and criteria are stored in the Tusk tasks.
