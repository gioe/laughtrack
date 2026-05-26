# TASK-2465: Laffs Comedy Cafe Ticket Target Audit

Date: 2026-05-26
Club: Laffs Comedy Cafe, club 1055

## Persisted ticket URLs

Current rows for club 1055 use one purchase target shape:

- `shows.show_page_url`: `https://www.laffstucson.com/coming-soon.html`
- `tickets.purchase_url`: `https://www.laffstucson.com/coming-soon.html`

The audited rows cover 40 shows from 2026-04-11 through 2026-06-14. Every ticket row is
`type = 'General Admission'`, `price = 0.00`, `sold_out = false`, and points back to the
coming-soon page.

## Live page behavior

The scraper's Playwright browser fetched `https://www.laffstucson.com/coming-soon.html`
successfully. The live page currently renders eight event forms for four comedians:

- Four reservation forms with `action="make-res-v2.php"`
- Four purchase forms with `action="tix2.php"`

The purchase form is not a stable direct GET target. A GET request to
`https://www.laffstucson.com/tix2.php` returns `Invalid email`.

Posting the purchase form data redirects to PayPal with show-specific checkout details:

- General seating: PayPal redirect with `amount=15.00`
- Preferred seating: PayPal redirect with `amount=20.00`

The PayPal redirect encodes the selected comic, date/time slot, and seating tier in the
query string, but that URL is generated from customer form input rather than published as a
static link on the listing page.

## Conclusion

The current coming-soon page target is the correct user-facing purchase target. Replacing
`purchase_url` with `tix2.php` would be worse because `tix2.php` requires POSTed customer
form data and is not a usable direct destination.

Remediation is still needed:

- The live reservation form action changed from `make-res.php` to `make-res-v2.php`, so the
  current extractor returns zero events from the live page.
- Ticket prices are recoverable from the purchase flow: general seating is 15.00 and
  preferred seating is 20.00. The current scraper persists only a 0.00 fallback ticket.

