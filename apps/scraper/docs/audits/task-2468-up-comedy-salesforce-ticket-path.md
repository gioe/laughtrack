# TASK-2468: UP Comedy Club Salesforce Ticket Path Audit

Date: 2026-05-26
Club: UP Comedy Club, club 187 (Second City Chicago, timezone America/Chicago)
Website: https://www.secondcity.com/shows/chicago/

## Persisted ticket URLs

Club 187 has 190 ticket rows spanning shows from 2026-03-28 through 2026-12-27. Every row
is `type = 'General Admission'` and every row has a non-null `purchase_url`. There is exactly
**one** purchase-URL shape in use:

- Base (before fragment): `https://secondcityus.my.salesforce-sites.com/ticket/`
- Fragment: `#/instances/<18-char Salesforce instance id>` (e.g. `a0FTP000009NIIP2A4`)

All 190 rows share that identical base; 164 of the 190 instance ids are distinct (a handful of
ids recur across rows). This is the PatronTicket purchase app hosted on Salesforce Sites — the
`#/instances/<id>` portion is a **client-side hash route** read by the PatronTicket SPA, not a
server path.

## How the fragment is handled in our code

Storage and rendering both preserve the fragment verbatim — nothing collapses it:

- **Scraper / storage:** all 190 stored URLs carry the `#/instances/<id>` fragment intact, so
  the scraper persists it correctly.
- **Detail-page CTA** (`apps/web/ui/pages/entity/show/ticketCta/index.tsx`): `pickTicketUrl`
  returns `ticket.purchaseUrl` unchanged; `mapTickets` (`apps/web/util/ticket/ticketUtil.ts`)
  copies it field-for-field. The value is handed straight to `next/link` `<Link href={url}>`,
  which does not strip fragments on absolute external URLs.
- **Show cards** (`ui/components/cards/show/index.tsx`, `.../compact/index.tsx`): render
  `href={purchaseUrl}` / `href={buyUrl}` verbatim.
- No `new URL()` reconstruction is applied to `purchaseUrl` anywhere in the render path. The
  only fragment-stripping code in the web app (`url.hash = ""`) lives in the comedian
  image-discovery utilities (`lib/admin/comedianImageDiscovery.ts`,
  `lib/admin/comedianImagePipeline.ts`) and never touches ticket URLs.

## Live page behavior

Loaded two sampled fragment URLs in a real browser (Playwright) so the SPA could execute the
hash route. Each opened the correct, distinct UP Comedy Club purchase flow, and the rendered
show date matched the stored Central-time value exactly:

| Instance id | Live "Buy" page title | Stored show date (America/Chicago) |
|---|---|---|
| `a0FTP000009NIIP2A4` | The Best of The Second City: Chicago-Style — Thursday, May 28, 2026, at 7:00 PM | Thu 2026-05-28 07:00 PM |
| `a0FTP000004XeKS2A0` | Best of The Second City — Saturday, May 30, 2026, at 3:00 PM | Sat 2026-05-30 03:00 PM |

The fragment is what selects the instance: navigating to a different `#/instances/<id>`
re-renders the SPA to that show. Without the fragment the base URL only shows the generic
PatronTicket landing.

## Conclusion

**Fragment URL handling is correct — no remediation needed.** The Salesforce Sites
`/ticket/#/instances/<id>` URLs are stored with the fragment intact and rendered verbatim end
to end. The hash route is consumed client-side by the PatronTicket app and resolves to the
correct UP Comedy Club show, with show dates matching our persisted data. Nothing in our URL
parsing or rendering collapses the fragment.

### Out-of-scope observation

26 of the 190 ticket rows reuse an instance id already used by another row (164 distinct ids /
190 rows). This is a minor dedup curiosity, unrelated to fragment handling, and was not
investigated as part of this audit.
