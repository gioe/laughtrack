# Non-public listings, activities and event formats

The deterministic rule family `comedy-event-rules-v1` recognizes bounded current
event offerings before the existing public write boundary. The classifier
version is `comedy-eligibility-v2-rules-v2`. This is independent of the unmerged
TASK-4160 v3 description-coverage work; a later merge must retain both changes
and issue a distinct classifier version if semantics change.

| Family | Reasons | Evidence |
| --- | --- | --- |
| `non_public` | `booking_promotion`, `private_event_closure` | Complete booking/closure title, or explicit assertion about this event/listing |
| `unrelated_activity` | `bull_rides`, `paint_and_sip`, `sewing_circle` | Complete activity offering title, or bounded current-event description assertion |
| `event_format` | `music_performance`, `karaoke`, `sightseeing_tour`, `games_sports` | Explicit concerts, tribute bands, EP/album releases, music open mics, karaoke, walking/ghost tours, bingo/trivia, sports viewing and wrestling |
| `comedy_format` | `live_comedy`, `mixed_comedy`, `musical_improv`, `comedy_band_camp` | Affirmative live-comedy performance billing and explicit combined formats |

The last two families use `comedy-context-rules-v1`. Family versions are
validated independently, so existing `comedy-event-rules-v1` evidence remains
valid and legacy three-field evidence retains its serialized shape. The changed
classifier version invalidates stale review/model fingerprints as usual.

Every matching evidence item records the family, rule version, reason,
provenance and exact cited text. Non-public availability is separate from genre:
it does not establish that the venue or private event never features comedy.
Unknown genre labels in the frozen development corpus remain unknown. Rule
matches are reproducible decisions to compare against that corpus, not new gold
labels or population false-positive estimates.

Description extraction only consumes the existing validated same-event detail
marker, including identity, selector and URL checks. Arbitrary show descriptions,
venue branding, biographies, price tags, public lineup names and platform IDs
are insufficient. Incidental amenities, generic booking advertisements, other
rooms/dates, negation and quoted/comedic titles do not establish activity billing.
Matching normalizes Unicode whitespace, compatibility characters, apostrophes
and hyphens while retaining the original cited text. Broad words such as band,
tour, movie, class and comedy alone do not establish a format. Venue suffixes
cannot supply positive comedy evidence. Narrow patterns intentionally miss
ambiguous cases. Only collected detail text
from the current supported adapter can supply description rule evidence; title
rules apply through the shared gate to every managed source.

A negative match rejects absent contradictory evidence. Explicit karaoke-and-
comedy, bingo-plus-comedy and comedic-tour billing except only the negative
phrase within that combined offering. Other matched formats in the same title,
separate description sentences, and independent platform categories remain
available to conflict. Musical improv and Comedy Band Camp do not become music
matches merely because their names contain music or band.

Ticketmaster segment/genre/subgenre names retain their existing event-category
semantics. Eventbrite subcategories 5010 and 103003 retain their adapter's comedy
evidence. Shared capture does not interpret bare Eventbrite category 103 because
its meaning differs between venue/organizer lists and search. Existing adapter
filters are unchanged; arbitrary platform IDs are not inferred as genre.

A match rejects absent contradictory evidence. Affirmative comedy plus a new
negative rule remains review, with the existing conflict reason protecting it
from optional model overrides. Existing blocked-only rejection, canonical-parent
resolution, majority-block review, and explicitly reviewed structural-label
exceptions retain their behavior. Identity membership never establishes comedy.
An explicit same-event denial of an activity or private closure is retained as
unknown evidence, so a matching title cannot override the contradiction. Its
existing invalid-evidence review reason also blocks optional model overrides.

The existing source modes control effects: `off` preserves publication without
staging, `shadow` records decisions while preserving publication, and `enforce`
withholds rejected/review candidates before show and related entity writes.
Existing human reviews and publication fences still apply. This change does not
update source configuration, enforce production cohorts, write performer blocks,
fetch live evidence or require a model provider.

Focused verification:

```sh
cd apps/scraper
PYTHONPATH=src:. .venv/bin/python3 -m pytest tests/integration/test_comedy_activity_rules.py tests/integration/test_comedy_context_rules.py -q
```

The tests include exact October 11 snapshot titles, guarded counterexamples,
serialized evidence replay, all three gate modes and identity regressions. The
separate TASK-4166 report will measure changes against the frozen baseline;
independent rollout validation remains TASK-4160.
