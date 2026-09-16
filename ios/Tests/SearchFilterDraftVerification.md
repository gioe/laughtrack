# Search filter drafts — TASK-4009

The Shows, Comedians, and Clubs filter sheets now own a draft for each presentation.
Tags, price changes, and Reset update only that draft. Apply publishes the selection
once; Close and interactive dismissal discard it without writing to the parent.
Reopening seeds a new draft from the current committed selection.

Each preview captures the presentation's search context, including text, location,
date range, sort, include-empty, home city, and pinned entities where applicable.
Preview requests reuse the normal endpoint/response classification but do not
replace parent results, update location warnings, seed favorites, or populate caches.
The facet list stays fixed during a presentation. Revision checks reject late
responses, including an A → B → A selection sequence.

The footer remains below the scrollable choices. It shows Updating results while
pending, a count only after success (including a real zero), or Preview unavailable
with Retry. Apply remains available in all three states. The price picker exposes
both its label and selected value to accessibility clients.

## Verification

- `ios/bin/test-sim LaughTrackTests/SearchFilterDraftTests`: seven tests cover
  isolation, one-shot Apply, cancel/reopen, stale responses, debounce, empty facets,
  honest count states, rendered states, and the three generated API clients.
- Six Search suites passed together on iPad Pro 11-inch (M4), iOS 18.3.1:
  SearchFilterDraftTests, SearchShowsFilterSheetTests, SearchRootViewTests,
  SearchRootModelTests, SearchQueryContinuityTests, and SearchShowsHeaderTests
  (62 tests total).
- Native NavigationTransitionUITests exercise price edits, Close, Apply, swipe
  dismissal, and reopening at standard and accessibility5 text sizes. Each
  presentation verifies that Apply is reachable at medium height, then expands
  the sheet to edit its price. The picker exposes the committed value on reopen.
- Fresh hosted captures were inspected on iPhone 16 Pro and iPad Pro 11-inch (M4)
  at standard and accessibility5 text sizes. They cover populated filters before
  and after scrolling, empty facets, confirmed zero, and failed previews. The
  footer remains visible and its content wraps at the narrow accessibility width.
  The current iPhone-only app runs in the iPad's 375 × 667 compatibility canvas;
  these captures do not represent a native iPad layout (tracked by TASK-4011).

Local evidence: `/tmp/task4009-after-phone`, `/tmp/task4009-verified-phone`,
`/tmp/task4009-verified-ipad`, `/tmp/task4009-ui-final.log`, and
`/tmp/task4009-ipad.log`, and `/tmp/task4009-gestures-verified.log`. Captures are also retained as test result attachments.

The baseline sheet tests and the required iOS compile gate passed. Initial test
iterations were corrected to compare numeric API prices, use the picker's stable
accessibility identifier, and wait for native menu dismissal before testing
whether the footer can receive a tap.
