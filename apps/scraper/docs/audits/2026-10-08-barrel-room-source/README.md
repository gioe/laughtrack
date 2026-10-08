# Barrel Room source disposition — TASK-4142

On October 8, 2026, disable source **77**, belonging to club **88**, because its
configured venue page no longer exposes SeatEngine Classic inventory and neither
reviewed ticketing feed currently supplies verified comedy. Preserve the club,
source identifiers/configuration, and every existing show and relationship.

## Evidence and scope

The venue's [events page](https://www.barrelroompdx.com/events) directly links
[Eventbrite organizer 80388668013](https://www.eventbrite.com/o/barrel-room-80388668013)
and its piano, jam, bass-DJ and email-list series. This is venue-linked ticketing
evidence; it does not certify a complete migration or any SeatEngine API ID.
The Eventbrite client fetched all pages of current public live organizer events:
151 entries across seven titles. Native descriptions classify all as music or
mailing-list products. Even the eight **Open Mic Night** entries explicitly say
they are for musicians. Performing Arts category 105 alone is insufficient:
the piano show is categorized there. No comedy was found.

The [legacy SeatEngine listing](https://www-barrelroompdx-com.seatengine.com/)
still exposes 36 Classic candidates, versus zero on the configured venue page.
These cover piano, jam, bass-DJ and open-mic series. The
[legacy open mic](https://www-barrelroompdx-com.seatengine.com/events/122875)
invites artists, singers and music lovers; it is not evidence of stand-up.
Legacy listing presence and a sold-out flag do not establish checkout validity
or inventory parity. Neither is needed to reject the currently non-comedy
inventory; no alternative legacy source is activated.

The existing metadata value 324 originated in a CDN namespace; neither it nor
historical API candidate 339 is certified by this work. No API ID is rewritten.
The existing 323 shows include historical comedy as well as music. Removing or
reclassifying those rows is outside this source-only repair.

`source-review.json` records capture time, exact counts, sample native URLs and
descriptions, HTML hashes, and the reviewed source before-image. HTTP fetching
used the scraper's own stack and the native Eventbrite client, not a summarized
API response. Raw responses remain private scratch artifacts.

## Repair and reactivation

Only `scraping_sources.enabled` for source 77 changes to false (the database's
timestamp trigger may also refresh `updated_at`). This stops the broken primary
feed without activating an unfiltered mixed-use organizer or introducing another
ingestion path. It does not hide or delete existing shows.

Before reactivation, verify newly available comedy against the venue-linked
native listing and choose an appropriate comedy inclusion filter. Do not treat
this dated finding as proof that the venue can never host comedy.

The dated repair script requires an exact reviewed plan and takes fresh private
snapshots covering the club, all its sources/shows, and all seven show-child
tables. Apply writes new mode-0600 recovery files before committing; recovery
refuses changed schema or affected after-state. Private recovery files must not
be committed. Focused PostgreSQL tests and live outcome are recorded separately.
