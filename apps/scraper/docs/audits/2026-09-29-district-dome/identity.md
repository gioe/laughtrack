# TASK-4069: District Dome postal conflict

Reviewed September 29, 2026. Club 554, source 87, SeatEngine venue 534.

## Decision

Use **21001 N Tatum Blvd, Phoenix, AZ 85050, USA** and structured ZIP
**85050**. Retain the name, website, Phoenix/AZ, America/Phoenix, country US,
Google business ID ChIJ_y7Ne-BwK4cR7wtdsKrbYgw and existing coordinates
33.676398899999995, -111.97365699999999. This is a postal-source conflict,
not evidence of a relocation or of a different physical business.

## Evidence and weighting

The [property operator's District Dome page](https://shopdesertridge.com/districtdome/)
explicitly locates the Dome within Desert Ridge Marketplace near Barnes & Noble
and Copper Blues, and gives 21001 N Tatum Blvd, Phoenix AZ 85050 in the Dome
location section as well as the property footer. The page describes a seasonal
immersive dining/cocktail attraction. Its seasonal promotion dates do not prove
current show availability, but the venue-specific physical directions are clear.

[Maricopa County permit FD-67827](https://envapp.maricopa.gov/Permit/PermitResults/FD-67827)
records Tikka Shack at the same street address with ZIP 85050, including a
June 22, 2026 inspection. This corroborates the property address, not the Dome's
individual suite or programming. It is not a USPS deliverability certification.

Google Places details for the existing business ID and a text search both name
The District Dome at this street address with the exact stored map point, but
report ZIP 85054. A building-address search also returns 85054. Preserve that
contradictory evidence in place-evidence.json. Prefer the property operator's
explicit Dome directions, independently supported by county address records,
over Google's ZIP. Do not move coordinates just to match a ZIP centroid.

The [current District Dome website](https://www.districtdome.com/) identifies
District Dome but supplies no competing street address. Direct authenticated
SeatEngine requests to /api/v1/venues/534, /venues/534/shows and
/venues/534/shows/291128 confirm account name, website and America/Phoenix.
API responses contain no independent postal address; see seatengine-evidence.json.
No credentials or access tokens are included in the evidence.

## Affected show and unresolved content anomaly

One stored and upcoming show: 522028, Carry On Airlines: Flight 111824,
source show 291128/event 104497, June 5, 2027 00:30 UTC. Live venue 534 feed
returns exactly that show and timestamp with 11 ticket inventories. Its 2024
flight label versus 2027 timestamp warrants review, but does not establish a
cancellation. The stored club description describes Carry On check-in at Wren &
Wolf, while the verified Dome identity is at Desert Ridge. Do not replace the
Dome's identity with Carry On or blindly move the show to club 600.

This postal repair preserves the show, its 11 tickets, 3 tags, 138 scraper-run
references and 23 purchase-click records, plus source ownership. No lineups,
favorites or saved-show references exist at the audit cutoff. before.json
captures all direct club/show foreign-key counts and fingerprints without
private user payloads. Source87 remains enabled; separate content triage must
review non-comedy disposition, description contamination and safe suppression.

## Recurrence

The actual SeatEngine venue upsert preserves nonblank existing ZIP values and
does not overwrite the street address or coordinates. Verify its real SQL with
stale 85054 metadata in a rolled-back transaction after the correction. Existing
ZIP preservation tests cover this path. No postal writer change is needed.
