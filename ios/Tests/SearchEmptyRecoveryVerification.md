# Search empty-state recovery verification

TASK-4010 replaces generic catalog-empty copy in Shows, Comedians and Clubs with a description of the active constraint and a focused action.

## Recovery behavior

| Active constraint | Action | Preserved |
| --- | --- | --- |
| Facets or show price | Reset filters | Names, location, dates, sort, presentation |
| Show date range | Search any date | Names, location, facets, sort |
| Effective nearby radius below 100 miles | Expand distance | ZIP, names, all other constraints |
| Effective 100-mile radius | Search everywhere | Names, dates, facets, sort |
| Comedian home city | Search all home cities | Query, facets, sort |
| Clubs limited to upcoming shows | Include all clubs | Query, location, facets, sort |
| Unrestricted query miss | Edit search | Existing text; scrolls to the input and opens the keyboard |
| Empty catalog or pinned entity with no editable constraints | No recovery button | No ineffective reset or invented availability claim |

Filters precede dates, distance, home city, availability, and text recovery. The next response can offer the next relevant action. This is based on active constraints, not a claim that removing one will guarantee matches. Retained empty results during a refresh or failure do not offer recovery for an unconfirmed query.

The effective Shows request determines whether distance applies. A comedian name searches nationwide; pinned clubs ignore ZIP. Neither receives a misleading distance action. Clubs hides its distance control when no ZIP is active, including after Search everywhere. A missing home-city facet in an empty response no longer silently clears the selected city.

Comedian discovery retains results with `showCount: 0`. Following remains available through the existing favorite action. No API or backend behavior changed.

## Automated coverage

`ios/bin/test-sim LaughTrackTests/SearchEmptyRecoveryTests` covers query misses, blank catalogs, dates, prices/facets, progressive distance expansion, club availability, pinned entities, preserving unrelated choices, retaining a selected home city, and finding/following a zero-show comedian through the generated API client.

`NavigationTransitionUITests.testSearchEmptyRecoveryPreservesQuery` and its accessibility variant exercise the live Search tab against `scripts/screenshots/fixture_server.py`: enter an absent club name, use the offered recovery actions, verify the draft survives, then use Edit search and continue typing into the same field. Fixture traffic is local.

Related Search root and Shows presentation tests were run on iPad. All touched iOS code is also covered by Tusk's configured Xcode build-for-testing gate.

## Visual evidence

Fresh captures use the live ShowsListView, ComediansDiscoveryView and ClubsDiscoveryView with confirmed empty responses, in the dark theme at standard (`.large`) and largest accessibility (`.accessibility5`) text sizes.

- iPhone 16 Pro, iOS 18.3.1: `/tmp/task4010-before-phone/`, `/tmp/task4010-after-phone/`.
- iPad Pro 11-inch (M4), iOS 18.3.1: `/tmp/task4010-before-ipad/`, `/tmp/task4010-after-ipad/`.
- AX5 after captures include both the initial viewport and a scrolled bottom view so the recovery action can be inspected.
- Native navigation captures are exported to `/tmp/task4010-native-captures/`.

The app currently runs on iPad in its iPhone compatibility canvas. These verify that shipping behavior; native iPad layout remains TASK-4011. At AX5 a card can exceed the viewport and is scrollable; its labels wrap and its action remains reachable. Short headings avoid splitting long entity names on the narrower compatibility canvas. Search recovery uses standard button density after native verification measured the old compact target at 39.7 points. Native tests check recovery buttons have at least a 44-point height.
