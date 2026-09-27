# Price-extraction audit — TASK-4056

## Result and scope

The fixed snapshot at 2026-09-27 02:17 UTC has **12,319 missing prices among
49,655 upcoming ticket records**. Grouping by the stored show last_scraped_by
attribute yields **23 clusters** with at least 50 tickets and at least 50% missing.
Those clusters contain 12,092 tickets, 10,491 unpriced: 85.2% of global missing
prices. The remaining 1,828 missing tickets are below this investigation's cluster
threshold. Ticket counts are not necessarily distinct show counts.

We established **274 baseline ticket rows with event-specific price evidence**:
270 positive admission amounts and four explicitly free admissions. This is a
conservative source-evidence lower bound, not an assertion that 274 tickets are
currently available or already repaired. Three samples had ended before probing
(Chaos Bloom free jam, UCB Sketch Cram, one Flop House show); availability, sale
windows, and identity must be revalidated before future persistence. Two CAD
Showpass samples and one Gallo seat-configuration sample are conditional and
excluded from the 274. No production records or scraper behavior changed.

Two distinct non-price anomalies also have direct source proof: **78 Que Sera
happy-hour promotions** and **one Standing Room Only season pass** are stored as
shows. Drink prices or pass prices must never fill ordinary admission gaps.

The old September 23 audit referenced by the task is absent from this checkout.
This report rederives the current cohort and uses its own saved SQL and results.
The threshold is by scraper attribution, not per venue or scraping_sources row;
last_scraped_by is a stored provenance proxy, not proof which source last changed
a particular ticket. Multiple venues are sampled where practical, with explicit
limits below. We do not extrapolate a sample to every record in its cluster.

## All qualifying clusters

Evidence counts include the four explicit-free cases and historical samples.
Zero means no safely established source-price example, not necessarily no price
exists anywhere. Mixed clusters retain narrower per-venue conclusions in their
findings files.

| Stored scraper attribution | Tickets | Missing | Baseline price evidence | Classification |
| --- | ---: | ---: | ---: | --- |
| ticketmaster_national | 6952 | 5799 | 0 | Upstream omission / supported priced exceptions |
| live_nation | 2344 | 1996 | 0 | Documented upstream omission |
| squarespace | 358 | 358 | 34 | supported extraction gap for products; heterogeneous event collections |
| up_comedy_club | 327 | 327 | 88 | supported extraction defect |
| ucb | 190 | 190 | 4 | supported detail extraction gap |
| tockify | 278 | 178 | 0 | intentional unknown fallback plus non-show contamination |
| ticketmaster_comedy | 162 | 162 | 0 | Documented upstream omission / unmatched sample |
| comix_roadhouse | 148 | 148 | 2 | supported_extraction_gap |
| seetickets_whitelabel | 137 | 137 | 3 | extraction_omission |
| mccurdys_comedy_theatre | 133 | 133 | 2 | supported_extraction_gap |
| grisly_pear | 133 | 133 | 131 | Supported detail extraction omission |
| squadup | 124 | 124 | 0 | upstream_list_limitation_and_protected_details |
| showpass | 101 | 101 | 0 | detail_enrichment_omission_with_currency_blocker |
| empire_comedy_club | 96 | 96 | 0 | unresolved_secondary_surface |
| tessitura_tnew | 92 | 92 | 1 | detail_enrichment_omission |
| zanies | 80 | 80 | 1 | supported_extraction_gap |
| flop_house_json | 74 | 74 | 2 | supported_enrichment_gap |
| holdmyticket | 74 | 74 | 0 | upstream_list_limitation_detail_unresolved |
| hennepin_arts | 63 | 63 | 0 | upstream_missing_checked_surface |
| denver_comedy_lounge | 61 | 61 | 1 | supported_extraction_regression |
| odoo_events | 57 | 57 | 1 | microdata_scope_omission |
| standing_room_only | 57 | 57 | 0 | upstream_missing_feed_checkout_unresolved |
| ticket_tailor | 51 | 51 | 4 | detail_enrichment_omission |

## Main actionable gaps

- **Grisly Pear (131):** actual detail JSON-LD provides base admission ($10/$20)
  and purchase controls provide totals ($12.37/$23.24) plus explicit fee breakdown.
  The listing-only model creates an unknown fallback. Exact source dates match
  for all 131. Show6331162 redirects to another date; show6039378 has no purchase
  control, so neither enters recovery. Extend existing TASK-4086 rather than open
  another competing detail-metadata implementation. Criterion13349/context712
  record price handling. Follow the current-calendar identity safeguards from
  TASK-4055 as well.
- **Squarespace (33 paid + one free):** two product collections expose real
  variant money values; parent priceCents=0 and inactive salePrice=0 are not free.
  Check stock, onSale, cents versus decimal money, and USD. One separate dated
  Chaos Bloom event explicitly advertises FREE admission and $0, unlike an
  unproven zero Halloween product or BCC's $5 OFF promotion. Product recovery and
  semantic event-detail free admission are separate tasks. Elysian legacy URL
  failed after redirect; Den sample has no offers. Do not apply product evidence
  to all 11 venues or all 358 tickets.
- **Second City/UP (88):** instances[].allocations[].levels[] already contain
  named dollar prices and fees; current ingestion discards them. All counted
  records match exact purchase URL and UTC time across five UP-associated
  resolvers. Eight URL matches with different times are excluded. Parse onSale
  and soldOut explicitly, including string False. TASK-4065 still governs room
  and date conflicts; do not fix identity by copying prices. Other two venue
  targets in this scraper cluster were not exhaustively sampled.
- **UCB (one paid + three free):** real dated details contain admission evidence,
  but listings never enrich it. Do not choose the cheapest arbitrary offer:
  ASSSSCAT's livestream11.96 is different from physical20advance/25door. Explicit
  Free Admission permits zero; no-price and mixed-offer cases remain unknown.
- **Port/SeeTickets (3):** calendar HTML already has positive list-view ranges
  ($29–39). Join by provider ID to the dated calendar event; no extra detail fetch
  is necessary. Zero price blocks do not establish free admission. TASK-4080's
  separate time-collision work does not authorize speculative price joins.
- **Ticket Tailor (4):** actual native fetcher retrieves detail JSON-LD, including
  three individually dated performances on one URL. Keep $50 Table for 2 distinct
  from $15 individual admission. Continental tiers24.75/28/38.75 are also exposed.
- **Odoo (1):** registration offers sit outside the Event microdata scope.
  Current extraction reproduces offers=[] while the event-associated form shows
  $15USD/InStock. Fix the Odoo adapter's form association rather than making the
  shared extractor collect unrelated document-wide offers.
- **TNEW (1):** Groundlings performance18662 has GA27. Gallo separately advertises
  seat prices39/59/69/99 plus9fees, but available-seat inventory was not verified;
  exclude it from recovery and exclude talkback/meet-and-greet add-ons from
  admission minima.
- **Comix (2), McCurdy (2), Zanies (1), Flop House (2), Denver (1):** source-specific
  omissions are proven by linked checkout15USD, venue Tickets26, visible37.95
  despite misleading structured0, Eventbrite AggregateOffer12.51/19.98, and
  streamed RSC GA21/VIP45 respectively. Denver's existing literal JSON-LD-only
  helper returns unknown; the shared RSC decoder can read the real target Event.
  Positive evidence is tied to exact IDs/dates, not generic venue prices.
- **Showpass (conditional):** public event detail API exposes CAD ticket_types
  absent from calendar responses. GA15 differs from displayed fee-inclusive17.11;
  other tiers include BOGO/dinner packages. Ticket has no dedicated currency
  field. The repair must establish currency-safe semantics end to end or keep
  unsupported amounts unknown; no silent CAD-to-USD substitution or guessed FX.

## Limitations and intentional unknowns

**Ticketmaster family: 7,957 missing across three attributions.** Existing
convention170 and TicketmasterScraper documentation explain missing priceRanges.
Current samples confirm absence for Bellhouse85 events, Punch Line Philly120, and Royal Oak41;
the Bellhouse query was repeated for different stored attributions and is not
170 unique events. A direct stored TJ Miller event also returns no range and
the actual client outputs an unknown ticket. Do not create a generic price fix
for this omission. Crucially, Irvine's different TicketWeb event feed now has
121 priceRanges records (119 positive, two zero); those URLs do not match the
sampled missing-ticket cohort. Existing code already consumes positive ranges
and handles TicketWeb zero placeholders. Thus the older blanket statement that
no API event ever exposes prices is too broad; available fields are supported,
and different event identities must not be joined speculatively. One further
venue query returned no events, which is inconclusive for prices.

**Squadup:** current v3 feeds still omit structured admission prices; a real
Playwright detail sample hits a challenge. A $100 bar-tab policy is not admission.
**HoldMyTicket:** list display price is empty and both HTTP/browser yield an app
shell with inconsistent embedded event identity; checkout pricing unresolved.
**Empire:** sampled listing/details lack offers; secondary checkout unexamined.
**Hennepin:** checked pages/Nuxt content lack admission dollars; 50% student rush
does not establish a base amount. **SRO:** all58 show records in the fetched feed
have null ShowPriceTierCosts; seat checkout unexamined. Preserve unknowns instead
of treating access failures or limited source surfaces as proof of global absence.

**Tockify:** all178 missing rows are explained at the checked surfaces:
22 Ice House Social Hour entries explicitly need no ticket and lack ticket links;
78 Bear City performances publish no admission amount;78 After Comedy Happy Hour
entries are drinks promotions. Existing ticket-button enrichment works for the
100 priced Ice House tickets in the cohort. Neither drink $3/$5 nor no-ticket
access wording should drive a broad price fill. Eligibility cleanup is separate.

**Etix context700:** the prior Raue zero-to-positive card range conflicts with
detail starting-at29. Its unknown fallback is intentional until actual applicable
ticket tiers are proved. That small subcohort does not meet the current audit
threshold; no unsupported price backfill is proposed. Original evidence remains
in docs/audits/2026-09-25-etix/task4052-price-filter-evidence.json.

## Evidence, validation and repair contract

queries.json, baseline.json, clusters.json, cohort.json, and sources.json retain
the production read-only queries and results. Credential fields in source configuration were omitted
from the retained export; raw broad query output is not a suitable publishable artifact. classifications.json covers all23
clusters; recovery-evidence.json contains274 distinct baseline ticket IDs joined
back to null prices. Each source team's findings JSON records real sample IDs,
scope, limitations and exact retained evidence. Parent findings preserve compact
all-row Grisly evidence and representative full HTML. Non-retained source files
are labelled captured_filename/retained_full_fixture=false; no raw capture is
promised merely because it was fetched. The root retention-manifest.json lists
the exact shipped files and hashes. Full raw files omitted from representative
manifests remain local scratch, not reproducible fixtures promised to readers.

Source checks used the scraper's actual HttpClient, native venue clients, or
Playwright stack. API counts came from decoded JSON, not text summaries. Source
probes and model/helper reproductions were read-only. Sources changed and some
performances ended between the fixed snapshot and later probes; fetch times
are recorded in the source manifests and must not be mistaken for one atomic
cross-system transaction.

Follow-up tasks have real positive and negative fixture contracts: exact dated
performance identity, ordinary per-person admission versus package/add-on/stream,
explicit free versus placeholder0, currency/units, fees, and sale availability.
No checkout purchase, enrollment or ticket reservation was performed. No blanket
NULL-to-zero update is appropriate. The frontend may use minimum paid price,
so protecting these semantics matters as much as increasing numeric coverage.
