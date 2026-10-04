# UCB physical admission evidence — TASK-4092

Checked 2026-10-03 through the scraper's HttpClient.fetch_html with curl-cffi
Chrome impersonation. These were read-only fetches, with no DB refresh.

Three current detail pages matched listing URLs, exact local start times, and
physical rooms:

| URL suffix under https://ucbcomedy.com/show/ | Local date/time | Physical admission |
| --- | --- | --- |
| craftmando-2026-09-05/ | October 3, 18:30 PDT, LA Annex | USD 7: 5 ticket + 2 fee |
| asssscat-la-2026-10-03/ | October 3, 20:30 PDT, LA Franklin | USD 29.95: 25 ticket + 4.95 fee |
| one-big-jam-2026-10-04/ | October 4, 17:30 PDT, LA Franklin | USD 0, explicit Free Admission |

All three physical offers say InStock. Paid ticket picker controls identify a
single admission, show quantity-based totals, and explicitly label fees included.
ASSSSCAT also offers USD 11.96 livestream (10 + 1.96 fee); it must never become
the physical minimum. Its description still advertises 20 advance / 25 day of
show, so current physical offers take precedence over descriptive price tiers.
The Craftmando URL has an old date slug: use startDate, not a date parsed from URL.
Compact HTML fixtures retain original JSON-LD, description, and ticket-picker
markup, excluding global navigation and unrelated tracking scripts.

Historical retained JSON evidence lives in
docs/audits/2026-09-27-price-extraction/platforms/:
16055-evidence.json explicitly states in-person tickets are 20 plus fees;
8834-evidence.json states 20 advance / 25 day-of-show, with only a livestream
structured offer. future8823, future8834, and future16055 explicitly proved
free physical admission at the September 27 snapshot. Regression tests replay
these original JSON-LD objects and exact quoted admission text in clearly
reconstructed HTML; they do not pretend the JSON audit retained original DOM.

All five historical URLs still match their historical event identity when
fetched now. Three retained physical-free offers are no longer present; do not
count them as current recoveries or use the remaining free livestream offer as
physical admission. The two paid descriptions remain source evidence, not live
inventory. Thus current sample recovery is 3/3 listing/detail matches; the
historical three free ticket recoveries remain unresolved in current sources.
No production ticket rows were updated, and these sample counts are not fleet
coverage estimates. The attempted nyc-14th-st listing facet yielded no cards,
so it supplies no current New York inventory evidence.

Policy: match URL, exact start instant, and physical room; accept only USD
individual admissions. Preserve explicit zero separately from unknown. Keep
sold-out/ambiguous offers unknown-priced and never replace them using marketing
text. Text-only prices include only stated amounts; retain plus-fees versus
unspecified-fee labels rather than invent a checkout total. Structured amounts
already include fees when the matching ticket picker says so—do not add twice.
