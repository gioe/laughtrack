# TASK-4070: Laugh Tonight is not the Jersey City Laugh Tour venue

Reviewed 2026-09-29. Club855 / source294 / SeatEngine424 remains a real comedy
promoter account; it is not a verified physical Jersey City venue. Zero upcoming
stored shows and zero current SeatEngine feed shows were returned. Do not invent
a replacement postal address or equate an account identifier with one building.

## Authoritative identity evidence

Live https://www.laughtonightcomedy.com/ and /calendar and /events contain empty
street/city/state JSON-LD and identify Laugh Tonight Comedy. API venue424 has
organization226, the matching website, and America/New_York account timezone,
but no physical address. The account formerly advertised Cornerstone in Muncie
in its description; that stale description remains in our database.

Live https://www.thelaughtour.com/ identifies The Laugh Tour, operated by Hugging
Bunnies Inc., inside Dorrian's at 555 Washington Blvd, Jersey City NJ07310.
https://dorrians-jc.com/comedy independently identifies and links The Laugh Tour.
Google place ChIJ369ARGdXwokRVCaKcxyCCBw is explicitly The Laugh Tour Comedy Club,
links thelaughtour.com, and returns (40.7280954,-74.034928). Those coordinates,
street and ZIP identify the OTHER business, not Laugh Tonight. No reviewed
source establishes common ownership. Even a Google text query for Laugh Tonight
returns Laugh Tour first: search rank does not establish identity.

## Historical assignments reviewed

| Stored show | SeatEngine show/event | Direct API evidence | Disposition |
|---|---|---|---|
|835461 Tommy Davidson|366585 /134774|Labels MUNCIE IN and CORNERSTONE CENTER FOR THE ARTS; 2026-05-10T18:00-04:00|Wrong Jersey City assignment; preserve pending physical routing|
|1441452 Henry Coleman|370667 /136528|Labels CHICAGO IL and LAUGH FACTORY CHICAGO; cancelled_at 2026-05-27T14:47Z|Wrong Jersey City assignment; cancellation and account-timezone ambiguity require explicit reconciliation|
|4340528 Darren Brand|380864 /140834|Label FUNNY PHAT FRIDAYS; 2026-08-21T21:00-04:00; no physical venue in API|Do not infer address from account; preserve pending review|

Research found an indexed official /events description naming Elite Rentals &
Events, 3401 N Shadeland, Indianapolis IN46226 for Darren Brand. Today's live
/events and old /shows URLs no longer display it; treat that as a historical lead,
not a current verified destination. The two direct API city labels already prove
that one replacement Muncie address cannot repair this promoter account.

The three shows retain eight tickets, six lineup links, six tags, 25 purchase
clicks and 138 scraper-run links. One comedian has home_club_id855. Counts and
full-row fingerprints of all direct club/show foreign keys are in before.json.
TASK-1984's source metadata calls duplicate449 the same venue; it established
shared SeatEngine424 ownership, not one physical location. Preserve the canonical
account and references; do not redo historical duplicate consolidation here.

## Reviewed repair

Hide club855 and classify it as producer; disable source294 with a
 task_4070_disposition stamp so national discovery cannot re-enable it. Clear the
foreign street, city/state, coordinates and Google place identity; retain blank
ZIP rather than borrowing07310. Replace stale venue description with the verified
multi-location promoter identity and disable its unverified image flag. Normalize
its verified website to HTTPS. Retain account timezone, source identity/URL, status,
all show dates and every linked record. Do not denylist the legitimate Laugh Tour.

Actual SeatEngine discovery upsert preserves visibility/address/place fields and
disabled sources carrying task disposition metadata. The client still stamps all
events with self.club.id and account timezone: TASK-4109 covers physical routing.
Re-enabling requires verified event locations and cancellation/timezone handling.
