# Second City allocation evidence — TASK-4091

Read-only checks on 2026-10-03 used the worktree's HttpClient.fetch_json and
HttpClient.fetch_html with curl-cffi (Chrome impersonation); no scrape persistence
or production refresh was performed.

The five resolver URLs are retained in
docs/audits/2026-09-27-price-extraction/platforms/manifest.json. Current results:
Grad Revue Preview: 3 instances; Clued In: 7; Not Today Santa: 25;
the fifth resolver: 53; Edie Arnold: no response data. Of the 88 historical
up-matched.json rows, 85 still match by exact purchase URL and UTC datetime;
3 are unresolved. These are source recovery candidates, not repaired DB rows.
The separate eight up-date-mismatch.json rows remain excluded from recovery.

The Clued In checkout for 6aa41ecbade1ed30a8af57e1 identifies seller The Second
City - Chicago, room UP! Comedy Club, currency USD, General Admission price 30
and an individual ticket quantity, corroborating resolver dollars per admission
(not cents or a table total). Resolver allocation fee is explicitly zero.
Checkout declares exclusive tax calculation: resolver price plus any explicit
allocation fee is NOT a claim that all checkout taxes/charges are included.
Do not invent checkout fees absent from the resolver. Missing/invalid fee or
price remains unknown. Only the verified US ticket hosts establish implicit USD;
foreign/unknown currency must not enter the currency-less Ticket price column.

Allocation soldOut contains string False/True. saleStatus is stale: retained
notAvailable/onSale=false instances still say On Sale. Explicit sale state wins.
Keep sold-out separate from closed/unknown sales: only explicit sold-out evidence
sets Ticket.sold_out; closed/unknown sales retain unknown-price tickets, with
the source state retained on the event. Ticket has no currency or general
availability column, so event metadata carries those distinctions.

Prices belong only to nested instance allocations with consistent IDs, the
configured room, and the same date used for Show conversion. Do not join by
title or URL alone. Preserve existing date conversion; if the local label
overrides a conflicting ISO instant, withhold price rather than attach another
performance's price. Existing GraphQL room filtering remains in force.

The context's TASK-4065 reference is unrelated (a completed seven-organizer
venue audit); it does not establish Second City room identity. Resolver address
must be checked directly. Grad Revue's address is e.t.c. Theater, not UP Comedy
Club. No production backfill is authorized by this evidence.
