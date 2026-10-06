# TASK-4117: District Dome non-comedy disposition

Reviewed October 6, 2026. Club 554 and SeatEngine source 87 / venue 534 remain
District Dome at 21001 N Tatum Blvd, Phoenix, AZ 85050, America/Phoenix.
This is distinct from Carry On club 600 / source 336 / venue 584 downtown.

## Evidence and decision

The [property operator](https://shopdesertridge.com/districtdome/) describes
District Dome as a seasonal immersive dining and cocktail experience with
projection displays and DJ programming. Its venue-specific directions confirm
Desert Ridge Marketplace and ZIP 85050. Seasonal dates on that page are not
proof of current availability or closure.

Fresh requests through the scraper HTTP stack fetched the property page,
District Dome website, Carry On website, and exact show page. The authenticated
SeatEngine client returns venue 534 named District Dome and one show: native
291128 / event 104497, Carry On Airlines: Flight 111824, June 5, 2027 00:30 UTC,
with eleven inventories and cancelled_at null. The 2024 flight label does not
establish cancellation. The [Carry On operator](https://www.carryonphx.com/)
explains its airline-themed cocktail reservations and Wren & Wolf check-in at
2 N Central Avenue, a separate location. Neither source establishes a comedy
performance or authorizes moving the Dome show to Carry On.

Disposition: hide club 554 from comedy discovery, classify it non_comedy, disable
source 87 with task_4117_disposition metadata, and replace the contaminated
Carry On description with a concise account of District Dome. Keep active status,
physical identity, reviewed postal correction, source ownership and URLs. Preserve
show 522028 without changing its cancellation flag, date, ID or venue. Preserve
all eleven tickets, three tags, and the currently twenty-eight click references.
Do not delete inventory, merge venues, or change any Google deny-list identity.
Existing disabled-source disposition retention already prevents SeatEngine
national rediscovery from re-enabling this source.

Before repair, a fresh public show-detail API request returned HTTP 200 for
522028, confirming the inventory remains publicly exposed. The database still
had visible=true and source enabled=true, with Carry On/Wren & Wolf description.
Raw native/API responses are held privately in /private/tmp/task4117-evidence;
source-evidence.json contains sanitized native identifiers and response hashes.
Execution, rollback instructions and discovery verification follow separately.
