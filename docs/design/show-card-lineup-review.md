# Show-card lineup review — TASK-4039

Implemented the approved B/D direction on 2026-09-23.

## Behavior

- General Search: full-width event title and venue, then a quiet **Lineup** band pairing a portrait with its name and a readable roster. No stacked-avatar footer.
- Contextual Search: a unique, normalized full comedian-name or alias match in confirmed current results enables **Matches your comedian search**. Partial, ambiguous, failed, stale, or empty queries use B.
- Followed-comedian Discover rails: a listed favorite enables **You follow**, a larger performer name, event details, and remaining lineup. Both legacy and policy-driven rails pass this reason explicitly; missing favorite information uses B.
- Portrait ranking does not establish billing. Cards retain supplied titles apart from surrounding whitespace, including parenthetical names, and do not generate billing labels.
- Names survive empty, invalid, and failed images. Canonical identities are deduplicated before overflow counts. Missing roster data reads **Lineup unavailable**.
- Whole-card navigation, selection attribution, date/time, venue, room, price, and sold-out/open-mic semantics remain intact. Decorative portraits are hidden from accessibility; adjacent text supplies their identity.

## Verification

Focused iOS 18.3.1 simulator suites passed:

| Suite | Tests |
| --- | ---: |
| ShowRowTests | 50 |
| ShowsListViewPresentationTests | 12 |
| HomeDiscoverRailPlanTests | 30 |
| SearchAgendaPresentationTests | 9 |
| SearchAgendaVisualTests | 2 |

```sh
ios/bin/test-sim LaughTrackTests/ShowRowTests LaughTrackTests/ShowsListViewPresentationTests LaughTrackTests/HomeDiscoverRailPlanTests LaughTrackTests/SearchAgendaPresentationTests LaughTrackTests/SearchAgendaVisualTests
```

The capture suite writes 24 task4039-<width>-<text-size>-row<index>.png files to the simulator app temporary directory and attaches them to the test result. It uses native SwiftUI at 375-point phone and 834-point tablet viewports, compact/regular size classes, the actual adaptive Search list/grid, and standard/AX5 text. Scroll positions include ensembles, solo performers, unknown lineups, overflow, long titles/names, free/sold-out states, contextual Search, and standalone followed cards. Fixtures intentionally include failed and absent portraits.

Reviewed the captures for title fidelity, portrait/name association, grouping, wrapping, and card boundaries. At AX5 cards grow beyond the viewport and remain vertically scrollable; text is not truncated to fit. Tablet captures preserve the existing two-column composition. Live Search was also opened in the updated app and captured.

The same 2 native capture tests passed on iOS 26.2 using test-without-building after the iOS 18 build. A direct iOS 26 build had stopped in asset-catalog compilation without a diagnostic; the existing simulator binary ran successfully on that runtime.

Local review artifacts: /tmp/task4039-review/index.html and /tmp/task4039-review/live-search.png. These are temporary evidence; the committed capture test is the durable reproduction path.

The iOS 18 hosted-view harness renders the followed card correctly (also checked with OCR) but exposes no accessibility activation nodes, even in isolation after snapshot and settling. Navigation coverage therefore exercises the actual button action and verifies its exact destination and a single attribution callback before navigation; it does not claim a synthesized tap. Accessibility ordering was reviewed in view composition: event/venue/lineup for B; reason/performer/event/venue/remaining lineup for D, with decorative portraits hidden. Hosted accessibility dumps also lacked nodes on iOS 26; spoken VoiceOver output was not verified by this harness.
