# Search query continuity (TASK-4002)

## Query policy

Search remembers independent Comedians, Clubs, and Podcasts drafts for the lifetime
of the mounted Search screen. Switching categories restores that category's draft;
clearing changes only that draft. Navigating to a detail screen and back preserves
the draft and the category's other filters. These drafts are not persisted across
app launches.

Shows keeps separate comedian and club constraints. Its visible field switches
between them with the Comedian and Club buttons; switching does not clear either
constraint. The existing labeled constraint chips remain individually removable.
A generic entity-category query is never silently applied to Shows.

Discover seeds replace only their destination category's draft. Shows seeds still
use the explicit ShowSearchSeed fields and existing location/date behavior.

Changing category or Shows input mode dismisses keyboard focus. Search submits
by dismissing the keyboard; Clear keeps the field focused and ready to type.
Detail navigation dismisses the keyboard without clearing text.

## Verification

- SearchQueryContinuityTests covers draft editing, clearing, category switching,
  Discover seeds, and independent Shows constraint removal.
- SearchRootModelTests and SearchRefreshContinuityTests retain coverage for seeds,
  pinned contexts, location inheritance, and honest cached-result state.
- NavigationTransitionUITests/testSearchQueriesSurviveCategorySwitchesAndDetailReturn
  drives real text fields, clear and mode buttons, category changes, and detail
  navigation against the screenshot fixture server on localhost:8765.
- SearchQueryVisualCaptureTests hosts the actual SearchRootView for all four
  categories, with network loading disabled to keep identical skeleton content.
  This isolates entry layout; it does not include the outer app navigation chrome.

Before/after captures use iPhone 16 Pro and iPad Pro 11-inch (M4), iOS 18.3.1,
at standard and accessibility5 text sizes. iPad uses the app's shipping iPhone
compatibility mode (TARGETED_DEVICE_FAMILY=1), not a native iPad layout.
Artifacts are copied to /tmp/task4002-{before,after}-{phone,ipad}-{category}-{size}.png.

The phone run passed 84 unique checks: 5 query-continuity tests, 9 root-view tests,
30 root-model tests, 26 entity-data-flow tests, 12 refresh-continuity tests, one
category-capture test, and one real navigation UI test. The UI test verifies
keyboard dismissal on mode/category changes and Search submit, continued focus
after Clear, and retained text after the native back gesture. Its full-app
screenshot, including both labeled Shows constraints, is /tmp/task4002-search.png.
