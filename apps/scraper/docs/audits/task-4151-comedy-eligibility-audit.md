# Parent-aware venue/feed contamination baseline — October 10, 2026

This is a triage report, not a count of venues where comedy never occurs. No production rows were changed. The snapshot contains 3,019 venues (2,763 visible), 142,375 retained shows and 120,039 raw lineup appearances. The upcoming boundary is October 10 at 00:00 UTC, inclusive; upcoming excludes cancelled shows. All-history includes every retained show, including future and cancelled rows.

| Visible venue signal | Earlier raw audit | Refreshed parent-aware audit |
| --- | ---: | ---: |
| Majority blocked appearances, all history | 70 | 70 |
| Entirely blocked appearances, all history | 52 | 52 |
| Majority blocked appearances, upcoming | 14 | 14 |
| Entirely blocked appearances, upcoming | 8 | 8 |

These counts overlap; do not add them together. The refreshed raw comparison also yields 70/52/14/8. Parent resolution rescues 292 blocked alias appearances across 75 venues (five upcoming appearances), but no venue crosses these thresholds. Deduplication reduces 120,039 raw appearances to 118,837 resolved appearances. Effective blocked appearances fall from 4,311 to 4,019. Upcoming raw/effective counts are 519/514. There are 2,541 blocked-only shows and 2,567 majority-blocked shows across all venues, including hidden venues.

The denominator is not the whole venue database: 2,235 visible venues have historical lineups and 1,658 have upcoming lineups. Across all venues, 72,697 of 142,375 shows have no lineup. Missing lineups are unknown, not clean comedy. Unblocked names are also unverified; they may be musicians or other performers.

## Semantics and limitations

- Follow integer parent IDs to a terminal comedian, rejecting cycles and missing links. A terminal visible root absent from the normalized deny list clears the alias block. A blocked terminal root blocks its aliases. An invalid chain cannot rescue a blocked original; an unblocked original with an invalid chain remains unknown.
- Normalize deny-list names with Unicode whitespace collapsing and casefolding. Casefold is slightly broader than SQL lower for some Unicode characters. Match lineup UUIDs to comedian rows before following integer parents.
- Deduplicate resolved identity within each show. Appearance ratios weight each show appearance; distinct ratios count each resolved identity once within the venue/feed window. Strict majority means greater than 50%; exactly half does not qualify. Empty denominators produce null ratios.
- Missing comedian rows are unknown. Broken/cyclic aliases retain separate unresolved IDs because their canonical identity is unknowable. Raw block reasons remain visible even after a valid parent rescues an alias. Reason counts count each distinct reason once per raw appearance; they are not deduplicated performer totals.
- The raw comparison reproduces direct identity/immediate-parent block flags and name denies before deduplication. It is a comparator, not the authoritative classifier.
- Blocked-only without valid parents is strong negative evidence. A blocked troupe/show name, such as The Second City or Sunday Funday at Cheaper Than Therapy, is not automatically exempt: independent affirmative event evidence is required. This audit does not infer such an exception from names or show_type and does not hide venues.
- One repeatable-read, read-only transaction retrieves all tables with a 120-second per-statement timeout. Resolution caches parent chains; there are no per-performer database queries. Memory use grows with snapshot size. An as-of boundary controls upcoming selection; it does not reconstruct the database as it existed on that date.

## Source attribution

Shows have no scraping-source foreign key. A unique club_id + last_scraped_by match is **inferred last-writer attribution**, not exact historical feed provenance; all source rows, including disabled sources and zero-show sources, are retained. Source-target feeds cannot be inferred from destination venues. Organizer IDs identify production companies and receive separate unresolved feed buckets. A production_company_id assigned by keywords is not source evidence.

| Attribution bucket | Shows |
| --- | ---: |
| Unique inferred venue source | 93,949 |
| Organizer feed, source unresolved | 2,936 |
| Multiple candidate sources | 759 |
| Missing last-writer key | 28,759 |
| No matching venue source, including aggregate feeds | 15,972 |

These buckets sum to 142,375 shows; each show is assigned once. Candidate source IDs and resolution/block evidence are retained for suspicious or rescued shows in the full output. A zero-show feed means no shows could be attributed to it, not proof the feed produced nothing.

## Harvelle's and candidate review

Harvelle's Santa Monica (club 475) has 248 retained shows, only 40 with lineups (16.1% coverage). Of 68 appearances, 27 are blocked (39.7%); nine shows are blocked-only and 13 majority-blocked. Its upcoming window has 51 shows, eight with lineups and 14 unblocked appearances. That does not certify a comedy-only calendar. Event-level eligibility remains necessary at mixed venues.

The companion JSON includes all 70 majority-blocked visible venues with both windows, reason counts, samples sizes and performer ratios. High-volume candidates include Empire Strips Back Theater, Hamburger Mary's Las Vegas, The Hook and Lincoln Center's Newhouse Theater. They are review candidates, not automatically classified as venues where comedy never occurs. Review independent event evidence and preserve occasional comedy at mixed venues. Existing TASK-3982 owns identity repair; TASK-4152 onward owns source policy, event gating and rollout.

## Reproduction and retained evidence

From apps/scraper:

```sh
.venv/bin/python3 scripts/core/audit_comedy_eligibility.py \
  --as-of 2026-10-10T00:00:00+00:00 --output /tmp/comedy-eligibility.json
.venv/bin/python3 -m pytest tests/integration/test_comedy_eligibility_audit.py -q
```

`task-4151-comedy-eligibility-baseline.json` retains the compact baseline: population totals, raw/corrected triage, attribution reconciliation, all 70 majority-blocked candidates, Harvelle's, and the SHA-256 of the full session report. The full 11.8 MB report is generated on demand rather than checked into Git. Production changes after this snapshot can change rerun results. Offline fixtures cover parent chains, alias deduplication, strict majority, missing evidence, cancellation/boundary behavior, ambiguous and organizer attribution, and the read-only transaction contract.
