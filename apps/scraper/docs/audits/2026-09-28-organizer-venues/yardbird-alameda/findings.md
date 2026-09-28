# Yardbird and Alameda venue audit

Read-only snapshot, upcoming cutoff **2026-09-28T13:45:00Z**. Public pages retrieved on 2026-09-28; exact timestamps and per-show evidence are in JSON. Raw captures remain in `/private/tmp/4065-ya/`, outside git. No production mutations or scraper fixes.

| Organizer club | Upcoming DB shows | Correct address | Confirmed mismatch | Unknown |
| --- | ---: | ---: | ---: | ---: |
| Yardbird Comedy 613 | 13 | 4 | 6 | 3 |
| Alameda Comedy 447 | 9 | 0 | 3 | 6 |
| Total | 22 | 4 | 9 | 9 |

“Correct” means physical event address matches the assigned club address, even though its display name is the producer. All 22 have individually retrieved detail pages and matching platform show IDs/start timestamps. Listing JSON-LD enumerates all 13 Yardbird and 9 Alameda shows. Yardbird's visible listing omits Joe Fenti from its main text but includes both performances in JSON-LD, so the audit does not mistake that presentation gap for absence.

## Findings

Yardbird stores **616 Grand St**, Willie McBride's. Sarper Guven (2 performances), Olivia Carter, and Marcus Monroe explicitly confirm this address. Daniela Mora and Bo Johnson (5 performances) explicitly say **Hoboken Biergarten, 1422 Grand Street**: six confirmed mismatches. Anthony Locascio and Joe Fenti (2 performances) provide only performer biographies and blank organizer address fields; their three venues remain unknown. Do not infer their venue from neighboring events, city name, or the configured club.

Alameda stores **2317 Central Ave**. Three Fireside Lounge performances explicitly specify **1453 Webster St**, confirming three mismatches. Six Cinema Grill events identify the restaurant by name but do not give an event-level street address. The [restaurant website](https://www.alamedacinemagrill.com/) publishes **2301 Central Avenue** and says it is within the Alameda Theatres Cineplex building. The [theater site](https://www.alamedatheatres.com/about) publishes **2317 Central Ave** and includes Cinema Grill in the same complex. These six are `unknown` / `same_complex_address_difference`, not proven cross-venue misroutes. Resolve the actual entrance and venue identity before changing the address. The organizer's own JSON-LD description says Alameda Comedy produces comedy at various East Bay venues; its location object is producer-level metadata with a blank street.

## Ingestion cause

Production `scraping_sources`: Yardbird source **259**, club **613**, enabled `seatengine`, API venue **618**, source URL `https://www.yardbirdcomedy.com/`; Alameda source **190**, club **447**, enabled `seatengine`, API venue **422**, source URL `http://alamedacomedy.com`. Both metadata objects are empty. Every audited show's `last_scraped_by` is `seatengine`; `scraped_by_organizer_id` is null.

Code path: `apps/scraper/src/laughtrack/core/entities/club/model.py` exposes the selected source's scraper and SeatEngine ID; `scrapers/implementations/api/seatengine/scraper.py:79` fetches that venue's shows; `core/clients/seatengine/client.py:59` constructs `/api/v1/venues/{venue_id}/shows`; `scrapers/implementations/api/seatengine/transformer.py` delegates to `client.create_show`; **`core/clients/seatengine/client.py:192` always sets `club_id=self.club.id`**. The source is an organizer account, but ingestion treats it as one physical venue. Room extraction only recognizes a small set of room labels and does not resolve these external event venues. A source-address edit cannot fix a multi-venue account.

## Coverage and cross-club search

The DB query included every upcoming show assigned to 447/613 **or** any upcoming show URL containing `yardbird` or `alamedacomedy`, across all clubs. It found no organizer-domain matches assigned elsewhere. A second cross-club search used all observed platform ID ranges plus event-title venue strings (Willie McBride, Hoboken Biergarten, Alameda Theatre Cinema Grill, Fireside Lounge). The sole numeric hit was unrelated DC Improv show 5911964 (`.../shows/384999`, Soyboyz); this was rejected because the hostname and event identity do not match. Numeric show-ID coincidences alone are not organizer attribution. No existing destination clubs matched the three Yardbird/Alameda destination venue names in a clubs name search.

## Focused follow-up

1. Add source-scoped event-venue routing for these SeatEngine producer accounts; preserve producer identity separately. Prefer verified event-level structured address, then bounded explicit description/title mappings. A generic JSON-LD location fallback would still choose the organizer and reproduce the problem.
2. Reassign only the **nine confirmed** upcoming mismatches after destination identity/address resolution and duplicate checks; preserve show IDs, ticket relationships and lineup associations. Four confirmed Willie McBride performances need no address repair. Resolve all nine unknowns separately.
3. Preserve an explicit unresolved route for biography-only Yardbird pages; do not silently assume Willie McBride's. Verify Cinema Grill's correct public entrance before choosing a physical club identity.
4. Canonicalize source/public URLs separately (Alameda HTTPS/www; Yardbird's current SeatEngine site) after checking live source configuration requirements. This is URL hygiene, not the venue-routing repair.
5. Keep producer visibility until every event is routed, consistent with Tusk convention 251; hiding an organizer while this scraper still stamps its club ID would hide its shows.
