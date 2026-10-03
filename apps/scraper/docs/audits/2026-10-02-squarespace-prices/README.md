# Squarespace variant price recovery — TASK-4089

The products parser discarded structuredContent.variants, then SquarespaceEvent
always produced a price-unknown fallback ticket. A captured Westside October 1
product (USD 8.00 / 800 cents) reproduced this before implementation.

## Current sources and identity

Fetched both sources with the scraper's HttpClient.fetch_json using its curl-cffi
session (Chrome impersonation), not a generic HTTP client. Capture timestamps,
website identity/location, product IDs, titles, URLs, descriptions, variants,
prices and stock are in source-evidence.json. Neither response had pagination.

- Westside Improv Studio, club 9075: https://westsideimprov.com/tickets?format=json
  — 15 products; source identity Westside Improv, 125 West Front Street, Wheaton IL.
- Rhino Comedy, club 16060: https://www.rhinoimprov.com/tickets?format=json
  — 21 products; source identity/address 96 Lafayette Avenue, Suffern NY.

Production scraping_sources configures both as products collections. Rhino also
excludes class, workshop and closed titles. The current products are dated shows.
Rhino's collection.fullUrl is misleadingly `/`; the configured `/tickets` endpoint
is the source used here.

## Admission, currency, fees and stock

Each captured product has one unnamed USD variant. Parent priceCents and
priceMoney are zero placeholders. Variant priceMoney contains dollars; legacy
variant price contains cents. Both representations agree. onSale is false;
salePrice zero is inactive and must not override the regular price. All current
variants have finite positive stock, unlimited=false.

Westside's additionalFieldsForm explicitly describes General Admission seating.
Rhino's standup listings describe individual table seating and purchasing tickets
separately; the Comfy Clash listings explicitly identify the USD 12 audience
admission, separately from a USD 10 performer registration link. Rhino's USD 35
fundraiser explicitly says one ticket includes pizza, water and the show: 35 is
that stated ticket price, not an invented admission-only breakdown. The USD 5
October 9 jam explicitly says it costs 5 to watch or play.

Rhino listings describe one/two-item minimums. Their cost is not included in the
stored base ticket amount. The sources do not establish checkout taxes or service
fees; none were estimated and no checkout/purchase was performed. Descriptions
retain those minimums and included items.

Conservative exceptions remain unknown: Thursday open mics advertise advance
performer access without establishing audience admission; October 30's post-show
jam says it is free for audience members despite a USD 5 variant; October 31's
Halloween event has an unproven zero with drink-special prices in prose. No prose
amount was treated as a ticket price.

## Database comparison and recovery

comparison.json records the pre-repair rows and source matches. Matching requires
club, full purchase/show URL, local-time-derived UTC instant, title (whitespace
normalized only), and General Admission ticket type. No fuzzy/event-neighbor
matching is used.

Of 36 current source products and 36 database ticket rows since October 1:

- 29 have a unique identity match and a verified positive admission price.
- 26 of those are future shows with unknown prices; these were targeted for repair.
- 3 matched priced shows are already past and were left unchanged.
- 7 products remain unresolved: five Thursday mics (one already past), the
  audience-free jam, and Halloween's zero placeholder. The past October 1 mic
  also fails the existing yearless-date parser's past-date gate.

repair-result.json records the transactional update and readback of the 26 future
tickets. Each UPDATE rechecks the original ticket/show IDs, venue, name, date,
URLs, type, future date, sold_out=false and price IS NULL. The batch aborts if any
row changed. Only ticket.price is written; no show, lineup, identity, URL, stock
or other ticket field is modified. This is separate from the ongoing parser fix.
The historical TASK-4056 count of 33 prices is not treated as a current target.

## Ongoing behavior and validation

The parser now passes verified base price and sold-out status into Show conversion.
It rejects non-USD/unknown currency, conflicting money/cents, nonfinite/negative/
zero/overprecision amounts, inactive sale amounts, unavailable/unknown inventory,
multiple or named variants, subscriptions/payment plans, uncertain packages and
explicit performer-only/audience-free ambiguity. A sold-out variant marks the
fallback sold out and leaves its advertised price unknown. Unlimited inventory
overrides a zero quantity. Standard Squarespace Events mode retains its existing
unknown-price behavior. No additional per-product network request is introduced.

Captured September 27 products cover Westside USD 8 and Rhino USD 5/20/35 plus
the zero placeholder. The dedicated regression suite checks cents, sales,
currency, stock, package/prose rejection and the mocked fetch-to-Show pipeline.
All 104 Squarespace tests passed before the commit gate; the required full scraper
suite is run by Tusk for each commit.
