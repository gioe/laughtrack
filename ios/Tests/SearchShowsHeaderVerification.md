# Shows header verification — TASK-4001

Fresh simulator captures used the actual ShowsListView inside a ScrollView with
the same root horizontal/top padding. The six-show fixture, ZIP 10012, Any date,
theme, and text sizes were identical before and after. This isolates the header
comparison; these are hosted component captures, not full navigation-shell shots.

| Simulator | Standard text, first ticket top | Largest accessibility text |
| --- | --- | --- |
| iPhone 16 Pro, iOS 18.3.1 | About 517 → 333 points (184 points earlier) | Removed the long introduction; controls stack and labels wrap. Results remain scrollable. |
| iPad Pro 11-inch (M4), iOS 18.3.1 | About 475 → 291 points (184 points earlier) | Verified the shipping iPhone compatibility layout. |

The app deliberately ships with TARGETED_DEVICE_FAMILY=1. The iPad run therefore
verifies the scaled iPhone experience; it does not claim native iPad layout coverage.
The isolated host filenames identify that compatibility idiom as phone, so compare
the simulator UDID in the test log when collecting iPad artifacts.

Visual review covered standard and accessibility5 header captures, plus Location
and Filters at the top and after scrolling. Header controls have minimum 44-point
targets. Calendar/view icons use 18-point artwork within 44-point targets. Date
and location constraints are represented by their controls rather than duplicated
below them. Custom ranges retain a visible date label. Price and secondary facets
remain reachable through Filters even when no facets are returned.

Focused verification:

- SearchShowsHeaderTests: date boundaries, Any date, local location/radius changes,
  independent price/facets, pinned comedian/club contexts, and Discover seeds.
- SearchShowsFilterSheetTests: actual sheet unmount restores both price and tags,
  including price-only results; captures standard/AX5 sheet layouts.
- ShowsListViewPresentationTests: compact pinned-list behavior and agenda/calendar.
- SearchRootViewTests: existing root navigation and query contracts.
- SearchRefreshPresentationTests: retained results, failure/retry, previous empty
  states, and unchanged scroll offset/content height during refresh.
- ShowsHeaderVisualCaptureTests: repeatable standard/AX5 real-view captures.

Capture tests print PNG paths in the simulator application's temporary directory
and attach the images to the xcresult when built with Swift 6.2 or newer. Session
comparison copies use /tmp/task4001-before-{phone,ipad}-{standard,AX5}.png and
/tmp/task4001-after-{phone,ipad}-{standard,AX5}.png. No API or server changes.
