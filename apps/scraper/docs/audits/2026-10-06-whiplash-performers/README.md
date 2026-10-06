# Whiplash performer identity review — TASK-4115

Reviewed 2026-10-06. The complete production association set contains 40 lineup
links across three candidate identities. [association-review.json](association-review.json)
records every show, source attribution, evidence URL, and disposition.

| Identity | Associations | Decision |
| --- | ---: | --- |
| Summer 2026 (518570) | 1, Whiplash | Keep its existing hidden status and block metadata; detach season/test-event label. |
| Grand Opening (2353268) | 1, Whiplash | Hide label record; detach opening-event label. |
| Heavy Hitters (2447993) | 38, six venues | Hide showcase/tour-label record; detach reviewed label associations. |

No candidate has aliases, favorites, podcast associations, or episode appearances
in the preflight query. Records themselves will be retained, not deleted or
converted into aliases. Every show and all other performer references are retained.

## Source-backed classification

- **Whiplash:** 26 associations, including 24 Heavy Hitters shows. Exact SeatEngine
  venue 650 show endpoints confirm the event and talent IDs for every association.
  Talent 52035 is Summer 2026 on Test Event: Summer Showcase; 54954 is Grand Opening
  on Invitation: Private Grand Opening; 54827 is Heavy Hitters on the Atlanta
  showcase. The [official site](https://www.whiplashcomedy.com/) describes the
  opening as a private celebration and the showcase as multiple comics.
- **Dallas Comedy Club:** its [official ticket page](http://www.prekindle.com/event/35488-heavy-hitters-dallas)
  describes a five-comic showcase, not a performer named Heavy Hitters.
- **Greenville, Greensboro, Jacksonville:** all 12 linked official show pages were
  fetched. They bill a tour featuring Darren Brand, Marvin Hunter, Burpie, and
  GiGi LeFlair separately from the Heavy Hitters title. Per-show URLs are in the JSON.
- **Macon:** the [official venue event page](https://www.maconcentreplex.org/event/heavy-hitters-of-comedy-legends-and-laughter-tour/)
  identifies the tour and names Earthquake, Adele Givens, Bishop, and MC Lightfoot.
  The direct Ticketmaster page returned bot verification and its Discovery API
  lookup returned no event; these failures were not interpreted as a cancellation.
  Existing Earthquake, Adele Givens, and MC Lightfoot lineup links are preserved.

All 40 candidate associations describe event, season, showcase, or tour labels.
No reviewed association establishes an individual performer with any of these
three names. Blocking these exact existing label identities is therefore justified;
there is no broad Heavy Hitters substring rule or guessed performer replacement.
The separately named Heavy Hitters Tour row at Greenville is outside the three
reviewed identities and is preserved for separate investigation.

## Prevention and cleanup boundary

The SeatEngine transformer filters the three exact normalized labels only for
Whiplash club 1347, source 591, venue 650. Other venues and genuine performers
remain unchanged. Existing hidden-comedian ingestion filtering prevents these
specific blocked database identities from reappearing through other sources.
No new global deny-list entries or performer aliases are created.

The cleanup uses a dated, guarded Python disposition script rather than a Prisma
migration, following conventions 79 and 325. It must validate the exact identity,
reviewed lineup set, source/show identities, and before-images; retain a private
backup before changes; and support guarded rollback. Production execution and
post-cleanup verification are recorded separately in verification.md.

Private before-images are retained outside Git. Public audit artifacts omit
operator account IDs and unrelated personal data. Fetch hashes reference the
private raw evidence; descriptions above summarize it rather than publishing
whole source pages.
