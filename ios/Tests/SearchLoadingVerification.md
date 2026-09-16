# Search loading verification — TASK-4008

Verified on September 16, 2026 with iPhone 16 Pro and iPad Pro 11-inch (M4), both iOS 18.3.1. Each capture set covers Shows, Comedians, Clubs, and Podcasts at standard and Accessibility XXXL text sizes, both as isolated loading components and within Search.

## Reproduce

From the repository root, keep the host awake during simulator runs:

```sh
caffeinate -dimsu ios/bin/test-sim LaughTrackTests/SearchLoadingGeometryTests
caffeinate -dimsu ios/bin/test-sim --model 'iPad Pro 11-inch (M4)' LaughTrackTests/SearchLoadingGeometryTests
```

The suite captures the actual Search views with loading models and inactive networking, using the existing SearchQueryVisualCaptureTests harness. Screenshots are attached to the Xcode result and written to simulator temporary storage; the log prints each path. Copy them before another app installation replaces that container.

## Evidence and observations

Fresh baseline captures are in `/tmp/task4008-before-phone/` and `/tmp/task4008-before-ipad/`. Final captures are in `/tmp/task4008-verified-phone/` and `/tmp/task4008-verified-ipad/` (16 images per set). `task4002-<category>-<size>.png` is the full Search composition; `task4008-<index>-<size>.png` isolates loading rows, with indices 0–3 corresponding to Shows, Comedians, Clubs, Podcasts. The inherited task4002 filename comes from the shared capture harness.

- Shows now retain the sort/view toolbar and reserve the agenda date heading. Tickets use the actual time/price strip, perforation, 60-point artwork, venue and room spacing. Calendar presentation remains visible during initial loading. Independent Library and pinned tickets retain their date stubs.
- Entity rows use the actual 56-point circle, rounded club logo, or podcast cover, quiet surfaces, typography and padding. Comedians reserve one title; clubs and podcasts include subtitle space. Favorite slots match the 44-point loaded target and clubs reserve the disclosure position.
- Large text uses the same vertical artwork/text arrangement and wrapping as loaded results. No horizontal clipping was observed in the inspected phone or iPad captures. Long rows remain scrollable.
- Placeholder content ignores hit testing and exposes one category-specific loading accessibility element. Invented counts, dates, names and placeholder controls are hidden from accessibility. The actual toolbar controls remain available with their existing minimum 44-point targets.
- Shared shimmer is subtler and returns static content when Reduce Motion is enabled. The regression toggles a running modifier into reduced motion and compares settled screenshots over time; it also checks static first render. This is a rendering check, not a physical-device VoiceOver announcement test.

The shipping app is iPhone-only, so the iPad simulator renders its existing 375-point compatibility canvas. These captures do not claim native iPad support. A separate geometry check verifies that the shared AdaptiveSearchResults composition uses two columns when given regular width, including accessibility text sizing.

## Regression checks

SearchLoadingGeometryTests has five checks: captures, entity geometry, ticket geometry, regular-width composition, and live Reduce Motion. All passed on both devices. The geometry checks compare fully rendered placeholder and loaded frames at 288 and 370 points, at standard and maximum accessibility text sizes.

SwiftUI redaction itself can change text wrapping: identical redacted text was one or two lines shorter than loaded text. The preservingSkeletonTextLayout modifier retains hidden unredacted text for measurement and overlays the redacted rendering. Keep this behavior when changing these rows; source-string assertions or build success alone do not catch this regression.

The focused existing regression run covers ShowRowTests, SearchAgendaPresentationTests, ShowsListViewPresentationTests, SearchFavoriteRowLayoutTests, SearchRootViewTests, and LibrarySavedShowsTests. The normal Tusk iOS build-for-testing gate also checks project synchronization and compiles all test targets.
