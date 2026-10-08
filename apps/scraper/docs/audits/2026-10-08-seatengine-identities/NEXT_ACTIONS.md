# Disposition, preservation and validation

## Source 77 — separately scope a source repair

The current website reciprocally binds Eventbrite organizer 80388668013, while
its configured classic extractor produces zero candidates. A follow-up should
compare current venue-linked ticket inventory against the legacy SeatEngine
inventory, verify comedy eligibility, establish a safe source choice, and
prevent duplicate ingestion before any configuration switch. Music, piano,
jam and mailing-list products must not automatically become comedy shows.

Do not blindly replace 324 with historical candidate 339, switch to the still
reachable legacy hostname, or enable the whole Eventbrite organizer. A reachable
legacy listing does not prove its ticket URLs remain valid. An Eventbrite
association does not prove all events migrated or that its entire feed belongs
in LaughTrack. Preserve current records until a separately scoped repair has
fresh before-images, exact-row guards and appropriate verification.

## Source 134 — retain classic Phoenix configuration

The configured URL is supported by the parent-domain redirect, SeatEngine's
hosted calendar and domain-bound structured identity. It remains parseable.
No source switch, replacement API ID, or geographic correction is supported
by the mismatch with API336. Historical candidate351 remains uncertified.
Any future API migration requires an explicit platform binding and inventory
comparison. Geo audits should interpret classic CDN metadata in its documented
namespace rather than infer venue identity from matching integers.

## Complete-row preservation

The probe used a PostgreSQL connection with `default_transaction_read_only=on`
and separate repeatable-read transactions before and after native HTTP checks.
It selected complete `to_jsonb` rows for clubs88/129 and sources77/134, then
compared all fields in memory. Both club rows and both source rows matched.
The evidence file contains matching keyed digests and row counts; the random
HMAC key was discarded. No private row bodies, credentials or headers were
published. No production writes or persistence scraper runs occurred.
Equality applies to the observation points, not every intervening instant.

## Validation

```sh
PYTHONPATH=src:. .venv/bin/python3 -m pytest tests/scripts/test_audit_club_source_geo.py tests/scrapers/implementations/api/seatengine_classic/test_pipeline_smoke.py -q
```

Result: **103 passed**, no skips. These existing tests cover native identity
binding, authorization-header isolation, read-only audit operation and classic
target selection. Parsing captured HTML additionally yielded 0 candidates for
source77, 82 for source134, and 36 for the legacy Barrel Room platform page.
Those counts describe extraction, not comedy eligibility or persisted shows.

The full scraper gate failed collection due to the existing missing `tzdata`
dependency. Three clean-HEAD precheck runs reproduced it with
`pre_existing=true`, `flaky_suspect=false`, `diverged_from_default=false`.
Path-limited Git commits followed the documented recovery; no unrelated
dependency or runtime code changes were made. The full suite did not pass.
