# Show times in browsers with older timezone data

Show cards, the show-detail ticket action, and the homepage hero share
`util/dateUtil.ts`'s `formatShowDate`. The formatter runs on both the server and
the browser. Updating Node's ICU data alone cannot update a visitor's browser.

For the following 2026 Canadian changes, the formatter applies the same explicit
presentation rules in both environments, without consulting the runtime's
timezone database:

| Venue IANA zone     | From this UTC instant, inclusive | Offset    | Display label |
| ------------------- | -------------------------------- | --------- | ------------- |
| `America/Edmonton`  | `2026-06-18T06:00:00Z`           | UTC−06:00 | ABT           |
| `America/Vancouver` | `2026-03-09T07:00:00Z`           | UTC−07:00 | PT            |

The IANA aliases `Canada/Mountain` and `Canada/Pacific` use the same respective
rules. Other Canadian zones are not inferred from their names or locations.

These are the legal effective dates at local midnight. Neither change moves the
clock at that instant: both regions were already observing their summer offset.
The rules prevent an obsolete browser database from moving the clock back in
November. Explicit labels also avoid differences between ICU/CLDR releases that
call the permanent offsets CST/MST or continue to use daylight-time names.

The formatter derives wall-clock fields from the UTC instant and the fixed
offset. It does not rewrite stored timestamps, venue timezone identifiers, API
values, ticket links, or countdown calculations. Older dates and other zones
continue through the existing `date-fns-tz`/Intl path; those depend on the runtime's
timezone data. This is a focused compatibility rule, not a bundled global
timezone database or a guarantee against future time-law changes everywhere.

The server's `npm run verify:timezones` build check remains useful for other
server-side timezone operations. Keep Node and browsers updated. If either
province changes its rules again, update the date-bounded display rules and
their boundary tests together. Revisit the ABT label if Alberta changes its
official naming regulation, currently scheduled for review by June 2031.

## Regression verification

Run the formatter tests with `TZ=UTC`, including the tests named `client` that
simulate older Edmonton/Vancouver rules using Denver/Los Angeles. Repeat under a
non-UTC host timezone to verify the compatibility path uses UTC fields. The
component hydration regression renders actual show cards and the detail ticket
action, then checks their text through React hydration with stale client Intl.
Historical dates, unaffected zones, November boundaries, and winter/summer dates
are covered separately from countdown behavior.

## Sources

- [Alberta's new time system](https://www.alberta.ca/albertas-new-time-system-abt)
- [British Columbia's permanent daylight saving time announcement](https://news.gov.bc.ca/releases/2026AG0013-000209)
- [IANA timezone source: northamerica](https://data.iana.org/time-zones/tzdb/northamerica),
  Edmonton and Vancouver zone definitions and accompanying 2026 legal-date notes
  (checked October 6, 2026).
