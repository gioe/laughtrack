# Search agenda hierarchy — TASK-4005

## Reproduce

Capture the real SwiftUI ticket component on both simulator devices:

```sh
caffeinate -dimsu ios/bin/test-sim LaughTrackTests/SearchAgendaVisualTests
caffeinate -dimsu ios/bin/test-sim --model 'iPad Pro 11-inch (M4)' LaughTrackTests/SearchAgendaVisualTests
```

The suite uses identical synthetic data and artwork fallbacks at standard text
and AX5, with separate solo, ensemble, long-title, sold-out, unknown-price, and
standalone cases. Additional AX5 captures scroll to the bottom so long rows can
be inspected completely. Copy the PNG paths printed by the runner before another
test launch reinstalls the app. The iPad runs the shipping iPhone app in its
375-point compatibility canvas; this is not a native tablet layout assessment.

For the native Search navigation tests, start the fixture server from the stable
primary checkout (so task worktree cleanup cannot remove its artwork files):

```sh
python3 scripts/screenshots/fixture_server.py --host 127.0.0.1 --port 8765
caffeinate -dimsu ios/bin/test-sim LaughTrackUITests/NavigationTransitionUITests/testSearchAgendaTicketsKeepDetailsAndNavigation LaughTrackUITests/NavigationTransitionUITests/testAccessibilitySearchAgendaTicketsKeepDetailsAndNavigation
```

## Intended behavior

Agenda date headings supply the calendar date. Tickets beneath them emphasize
show time and price in a full-width strip, with a horizontal perforation that
retains the warm paper-ticket treatment. Titles and venue details use the rest
of the card width. At accessibility sizes the time, price, artwork, and text
stack, and text can expand vertically.

Standalone tickets and compact lists without date headings retain the date stub.
Generated performer headlines and named shows starting with the full performer
name and a clear separator (colon, ampersand, or spaced dash) omit the repeated
subtitle in the agenda. Other event titles and aliases retain the featured
performer's identity. Room names,
supporting lineups, sold-out badges, and struck-through previous prices remain
available. An unknown price does not become a free ticket.

## Verification results

Fresh before/after captures on iPhone 16 Pro and iPad Pro 11-inch (M4), iOS 18.3.1:

- Baseline: repeated date stubs squeeze venue names and cap titles at two lines.
  At AX5 the date stays tiny while performer and venue text truncate.
- Updated: time and price scale with Dynamic Type. Titles, venue, room, and
  supporting credits wrap without line caps. Both narrow canvases retain the
  whole text column, and oversized tickets scroll vertically.
- Solo generated headlines no longer repeat the performer subtitle. Named
  ensemble shows keep their featured performer and supporting credits.
- Sold-out tickets keep readable details, the availability badge, and the
  struck-through previous price. Missing prices remain absent.
- A standalone comparison retains the full date stub.

The focused regression suite measures title growth and containment at 288- and
500-point widths, with and without performer artwork, at standard text and AX5.
It also covers distinct room names, canonical aliases, name-prefix collisions,
venue timezones and fallbacks, and unknown/free/sold-out prices. Existing Search
presentation tests protect the compact-list default and agenda-only opt-in.

All 65 focused tests passed across SearchAgendaPresentationTests, ShowRowTests,
and ShowsListViewPresentationTests. Both native Search agenda tests passed at
standard text and AX5, checking full accessible labels, venue-local time, price,
room, screen containment, a minimum 44-point target, and opening show detail.
Both device capture suites and the full iOS build-for-testing gate passed.

```sh
caffeinate -dimsu ios/bin/test-sim LaughTrackTests/SearchAgendaPresentationTests LaughTrackTests/ShowRowTests LaughTrackTests/ShowsListViewPresentationTests
```

Session artifacts: `/tmp/task4005-{before,after}-{phone,ipad}-*.png`. The baseline
used the ticket implementation at `bd131dc4a714`; the capture suite regenerates
the current implementation and a standalone comparison.
