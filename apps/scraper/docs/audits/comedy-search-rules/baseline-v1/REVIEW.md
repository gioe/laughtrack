# Frozen development review

`labels.json` records an agent review completed at its `review.reviewed_at`
timestamp, before proposed ingestion rules were run. The reviewer was
`codex:/root/corpus_labels`, not a human or independent blind evaluator.

The selection includes all 212 flagged occurrences from the original audit
(161 exact venue/title groups), plus 26 comedy controls (19 groups). Every
selected occurrence was checked against its own raw title and description.
Descriptions were identical within the selected repeated groups; each
occurrence nevertheless retains its own evidence reference and label.

| Selection | Comedy | Non-comedy | Unknown | Total |
| --- | ---: | ---: | ---: | ---: |
| Original audit flags | 28 | 14 | 170 | 212 |
| Deliberately selected controls | 26 | 0 | 0 | 26 |
| Reviewed selection | 54 | 14 | 170 | 238 |

The remaining 2,648 snapshot occurrences are **unreviewed**. They are not
comedy controls or unknown judgments made by the reviewer. These selected
counts cannot estimate a population false-positive rate or missed-comedy recall.

The original 56 strong flags are triage hypotheses. The frozen review requires
more than a suggestive name for a non-comedy judgment. Detailed music billing,
karaoke instructions, televised NFL viewing, mechanical bull rides, and actor
meet-and-greet programmes support the 14 non-comedy occurrence labels. Sparse
music titles, ghost tours, ballet titles and ambiguous acts remain unknown.
No additional event-detail webpages were fetched. These are judgments about
the programme advertised in the preserved API evidence, not independent
verification of what occurs in person or a guarantee that no comedy segment
could be omitted from the listing.

Genre, format and public availability are separate. The Addams Family is
labeled comedy and screening. Comedy classes retain comedy genre and training
format. The business mixer, RPG improv workshops, acting class for stand-ups and
stage-combat workshop retain unknown genre.
Booking promotions and private-event closure notices are non-public without
an invented genre. A mixed open mic that permits comedy remains unknown as to
whether comedy occurs in that particular performance.

The controls deliberately cover student/graduation audience shows, musical
improv, a team called Garage Band, Comedy Band Camp, Movie Pass improvisation,
comedic variety hosting, bingo with stand-up, karaoke with comedy, a comedic
tour, and drinks-special titles with actual event-specific comedy billing.
Comix venue footer promotions are not used to establish genre. Public lineup
names, club branding, price tags and familiarity with performers are not
treated as proof of comedy, blocked status or canonical parents.

## Identity mapping provenance

`mapping-query.sql` and its complete bound ID array in
`mapping-query-ids.json` were executed in one read-only, repeatable-read
PostgreSQL transaction. `mapping-query-result.json` is the raw row result;
`mappings.json` adds resolution status and byte digests. The transaction time
and `transaction_read_only=on` are recorded in mapping provenance.

All 2,886 public show IDs were present at this later database capture. Only 67
had a stored `source_performance_id`; these are retained as native identifiers
separate from public IDs. No queried show had a publication-linked candidate,
so every `source_id`/`event_key` mapping remains unresolved. `show_page_url`,
`last_scraped_by`, and organizer identity are retained as recorded, but none is
converted into an invented scraping-source mapping. No venue-wide source
join, URL parsing, blocked-comedian inference or production write was used.
The later database read cannot prove the exact mapping state at API capture
time.

Follow-up work must keep these label and mapping bytes frozen when comparing
rules. New evidence or revised labels require a new version and an explicit
change record. This exposed development corpus does not satisfy TASK-4160's
independent fresh-event validation requirement.
