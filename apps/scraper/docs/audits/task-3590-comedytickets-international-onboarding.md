# TASK-3590 ComedyTickets International Onboarding

ComedyTickets was used only as a discovery signal. No ComedyTickets URL was used
as a route target or enabled scraper source.

## Enabled Sources

The migration `20260706004000_onboard_comedytickets_international_verified_sources`
adds 10 idempotent club/source pairs:

| Venue | Country | Source | Smoke result |
|---|---:|---|---:|
| Boom Chicago | NL | `ticketmaster_comedy` | 19 future shows |
| 3Arena | IE | `ticketmaster_comedy` | 8 future shows |
| Bristol Hippodrome | GB | `ticketmaster_comedy` | 5 future shows |
| Edinburgh Playhouse | GB | `ticketmaster_comedy` | 8 future shows |
| Eventim Apollo | GB | `ticketmaster_comedy` | 20 future shows |
| O2 Apollo Manchester | GB | `ticketmaster_comedy` | 11 future shows |
| Club Regent Event Centre | CA | `ticketmaster_comedy` | 9 future shows |
| L'Olympia | CA | `ticketmaster_comedy` | 35 future shows |
| Leicester Square Theatre | GB | `ticketmaster_comedy` | 39 future shows |
| Laugh Shop Calgary | CA | `showpass` | 21 future shows |

The Ticketmaster rows are international venues outside the US-only national
Ticketmaster scraper. Each uses a verified Ticketmaster venue ID and the focused
comedy scraper. Laugh Shop Calgary uses the generic Showpass calendar API
verified from the venue's first-party site.

## Skips And Aliases

Existing records were reused instead of duplicated:

| Candidate | Existing club |
|---|---|
| House of Comedy New Westminster BC | `2357` House of Comedy British Columbia |
| Rick Bronson's House of Comedy BC | `2357` House of Comedy British Columbia |
| Rick Bronson's - The Comic Strip | `2358` The Comic Strip West Edmonton Mall |

Unsupported or ambiguous candidates remain unmodified and are documented in the
CSV report:

- Aruba Ray's Comedy Club, Comedy Bar Toronto/Danforth, Laugh Lounge, Le Point
  Virgule, and Monkey Barrel Comedy were checked against first-party pages but
  did not expose a supported generic source in this pass. They need
  venue-specific scrapers or a newly documented platform.
- Club Soda, Rebecca Cohn Auditorium, and Salle Pierre Mercure have either no
  verified supported source or zero future comedy results from Ticketmaster.
- OVO Hydro returned comedy-classified Ticketmaster rows, but the feed includes
  `Venue Premium` add-on products not filtered by the current focused scraper, so
  it was intentionally not enabled.
- Hotel Blackfoot is covered by Laugh Shop Calgary, the comedy venue in that
  property.
- Monkey Barrell Comedy is a duplicate/misspelling of Monkey Barrel Comedy.

The machine-readable disposition list is in
`apps/scraper/docs/audits/task-3590-comedytickets-international-onboarding.csv`.
