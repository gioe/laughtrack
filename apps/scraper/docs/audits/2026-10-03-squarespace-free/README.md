# Dated Squarespace free admission — TASK-4090

## Source verification

Chaos Bloom Theater (club 11295), 70 South Broadway, Denver, CO. Production
scraping_sources uses https://chaosbloom.com/api/open/GetItemsByMonth with
collectionId=5f63a332aa0558099ec5dd1b. October 2026 was fetched through the actual
scraper HttpClient/curl-cffi stack, then each of four FREE Improv Comedy Jam
calendar URLs was fetched with ?format=json through the same stack.

source-evidence.json preserves capture times, website identity, exact dated event
items and their embedded admission products. The products explicitly say
"FREE ALL Improv Comedy Jam Saturdays 9p-10p". Both product and sole unnamed
variant state USD 0.00. Product published=true, soldOut=false, onSale=false;
variant soldOut=false, unlimited=true. Quantity zero is therefore not sold out.
This is unconditional jam participation/admission, not free drinks, a member
promotion or a zero-valued parent placeholder. No required fee is stated in the
admission product; checkout fees/taxes were not independently tested. No checkout
or purchase was performed, and no fee was invented.

The historical September 26 example in the TASK-4056 audit remains a historical
anchor, not a repair target. Its whole-second rendered date and the database's
millisecond timestamp explain the permitted subsecond comparison tolerance.
The new frozen regression fixture captures the current October detail's exact
structured evidence instead of fabricating structured fields from the older
visible-text excerpt.

## Prerequisite calendar compatibility

The current October API has 37 records, each lacking a top-level id/startDate.
Dates live at structuredContent.startDate. Before this change the extractor
rejected all 37, so free-price enrichment could not run at all. It now accepts
recordType 12's nested-date shape and uses a validated relative event URL as an
internal identifier. All 37 URLs are unique; only 23 systemDataId values exist
because that field identifies reused artwork. It must never identify shows.
Legacy native-ID/top-level-date records remain supported.

## Database recovery

comparison.json holds the 32 existing ticket rows since October 1, split into
four source-verified free admissions and 28 unresolved/unmodified tickets. Matches
require venue, exact show/purchase URL, whitespace-normalized title and same UTC
start second. No title-only or recurring-series match is accepted.

The four current matches are October 3, 10, 24 and 31 at 9 PM America/Denver
(UTC dates October 4, 11, 25 and November 1). repair-result.json records four
price-only updates from unknown to 0.00 and an independent post-commit readback.
The transaction rechecks exact IDs, venue, original title/date/URLs, ticket type,
future start, price IS NULL and sold_out=false, aborting if any row differs.
No show/lineup/identity/availability field is changed.

October 17's stored jam (show 4930626 / ticket 5571698) is absent from the current
calendar and stays unknown. Absence does not establish cancellation or a free
price. The other 27 tickets do not have the scoped free-jam proof; their prices
are unchanged. Current recovery is four, not an extrapolation from a recurring
product or a historical inventory count.

## Ongoing guards and tests

Free evidence is evaluated during the existing per-event JSON detail request;
there are no additional network calls. It requires matching detail URL, title
and start time, CalendarEvent metadata, the explicit free-improv-jam name on
both event and embedded product, one available unnamed variant, and USD zero
on both product and variant. Positive existing event prices, sale/discount/
conditional wording, unavailable stock, other currencies, ambiguous/multiple
products and malformed detail are rejected. Missing evidence leaves price
unknown. Detail fetch failure preserves the show.

The positive-only product parser from TASK-4089 remains unchanged. Halloween's
unproven zero, free-drink prose and zero parent placeholders remain unknown.
This deliberately supports the verified free-jam pattern; it does not attempt
an unrestricted natural-language interpretation of all free offers.

All 153 Squarespace tests passed, including 49 new cases. Tusk's full scraper
test gate runs on each implementation/audit commit. No production scrape was
run to avoid unrelated ingestion changes during the targeted repair.
