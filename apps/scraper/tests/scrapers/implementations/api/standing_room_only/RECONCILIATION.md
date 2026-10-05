# TASK-4104 — Standing Room Only season pass

The retained September27 audit identifies parent event536, Summer Season Pass,
and child1655 with an artificial September30 2026 15:00 local date. Its real
description says it covers all shows except special events during the summer,
and is sold only at the box office. This is a multi-performance product, not
admission to a dated show. The source's literal September31 end-date wording
is not used to infer a performance date or price.

Replaying the retained feed at September27 reproduced conversion to a show.
On October5 the native StandingRoomOnlyScraper.post_form call returned20 live
parent events; event536 was no longer present. Boomer Broads event530 was a
current positive control with four October8–10 showtimes. The retained feed's
ordinary performances also have bActive=false, so that flag is not a filter.

The extractor now rejects full product labels such as season passes and
memberships before expanding Shows. Ordinary titles and descriptions mentioning
passes, members or box-office sales remain accepted. Ticket prices stay unknown.
The regression freezes audit time so past-date filtering cannot mask the defect.

Production inspection verified show3434154, ticket3773351, club11473, exact
event536 URL, title, source key and September30 19:00 UTC timestamp. Dependencies:
one ticket, one tag link,25 clicks; no saved shows, notifications, lineups or
discovery feature snapshots. Club inventory was94 shows; the other93 shows had
93 tickets, all with unknown prices. The recovery JSON contains only the
show/ticket/tag snapshot and aggregate counts, with no click/user payloads.

The migration was first validated against production data in a rolled-back
transaction, then applied as the sole SQL migration in a committed transaction
on October5. It locks the target, verifies identity, rejects changed tickets or
prices and protected dependencies, and deletes only that exact ID. It verifies
that all25 click records and attribution fields survive unchanged except show_id,
which becomes NULL via the existing foreign key. Club total_shows is refreshed.

After: zero target rows; all93 other show IDs and ticket IDs/prices unchanged.
A second rolled-back execution deleted zero rows, verifying safe replay.
Only this SQL was applied; normal Prisma deployment will record the migration
in its ledger. The code filter takes effect when the updated scraper runs.
