# Search category navigation verification — TASK-4003

Verified on 2026-09-15 against baseline `7b862a548acd`.

## Visual comparison

`SearchCategoryVisualCaptureTests` mounts the real `AppShellView`, including
the account button, category navigation, Search content, and bottom tabs.
An offline transport keeps content deterministic. Captures use `.large` and
`.accessibility5` Dynamic Type, with Shows and Podcasts selected.

| Simulator | Presentation | Before | After |
| --- | --- | --- | --- |
| iPhone 16 Pro, iOS 18.3.1 | 402 × 874 points | Podcasts clipped on entry; category labels ignore Dynamic Type | Four full labels at standard size; scalable, scrollable labels at AX5 |
| iPad Pro 11-inch (M4), iOS 18.3.1 | 375 × 667 points, shipping iPhone compatibility mode | Podcasts entirely offscreen on entry | Four full labels at standard size; selected label fully revealed at AX5 |

Title-case labels replace uppercase dotted capsules and glow. A three-point
underline communicates selection independently of color. Account artwork is
34 points inside its unchanged 48-point target; category targets are at least
44 × 44 points. At AX5, partial adjacent labels indicate horizontal continuation;
the selected label remains fully visible. The background follows measured header
height so enlarged text does not create a seam below the navigation.

Local artifacts follow `/tmp/task4003-{before,after}-{phone,ipad}-{shows,podcasts}-{standard,AX5}.png`.
Swift Testing also records images as xcresult attachments. Export those before
later Xcode runs rotate old result bundles. These local files are verification
artifacts, not committed app assets.

## Interaction and regression checks

- `testSearchCategoriesFitAndAccountRemainsReachable`: iPhone SE (3rd generation),
  375-point width; all four categories fully visible without scrolling, targets
  at least 44 points, exactly one selected accessibility trait, Account drawer
  opens and dismisses while retaining Podcasts.
- `testAccessibilitySearchCategoryRevealsAndRestoresSelection`: iPhone SE at
  accessibility XXXL; swipes to Podcasts, selects it, scrolls it out of view,
  visits Discover and Library, then returns to a fully revealed selected Podcasts.
  Discover and Library retain their account control without category navigation.
- `AppShellViewTests`: 19 checks cover retained Discover composition, Search pivot
  caching, shared account geometry, authentication, favorites, and shell behavior.

Run the focused checks with the repository simulator selector:

```sh
ios/bin/test-sim LaughTrackTests/AppShellViewTests LaughTrackTests/SearchCategoryVisualCaptureTests
ios/bin/test-sim --model 'iPad Pro 11-inch (M4)' LaughTrackTests/SearchCategoryVisualCaptureTests
ios/bin/test-sim --model 'iPhone SE (3rd generation)' LaughTrackUITests/NavigationTransitionUITests/testSearchCategoriesFitAndAccountRemainsReachable LaughTrackUITests/NavigationTransitionUITests/testAccessibilitySearchCategoryRevealsAndRestoresSelection
```

The UI tests require `scripts/screenshots/fixture_server.py` on port 8765.
They use sample data and do not write to production. The screenshot harness now
finds the horizontal scroller by its child button; a parent accessibility ID no
longer risks overwriting the category button IDs.
