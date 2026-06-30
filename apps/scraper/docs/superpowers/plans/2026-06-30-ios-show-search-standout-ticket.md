# iOS Show Search Standout Ticket Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make exactly one currently loaded iOS show-search result render as a premium ticket based on an internal popularity score, while removing popularity from the visible show-sort UI.

**Architecture:** Keep ranking policy in the show-search list layer, not inside the reusable row. The web API exposes an internal `popularityScore` number on `Show`; iOS decodes it and `ShowsListView` computes one standout show id from loaded items. `ShowRow` only renders the requested presentation.

**Tech Stack:** SwiftUI, Swift Testing, generated Swift OpenAPI types, Next.js API route DTOs, Vitest.

---

### Task 1: Remove Visible Show Popularity Sort

**Files:**
- Modify: `ios/Sources/LaughTrackApp/Search/Models/SearchOptions.swift`
- Test: `ios/Tests/LaughTrackTests/SearchRootViewTests.swift`

- [ ] **Step 1: Write failing Swift tests**

Add expectations to `searchRootModelUsesUnifiedSearchState()`:

```swift
#expect(ShowSortOption.allCases.map(\.title) == ["Earliest", "Latest", "Low price", "High price"])
#expect(!ShowSortOption.allCases.map(\.rawValue).contains("popularity_desc"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /private/tmp/laughtrack-ios-show-standout/ios && swift test --filter SearchRootViewTests/searchRootModelUsesUnifiedSearchState`

Expected: FAIL because `ShowSortOption.allCases` still includes `Popular`.

- [ ] **Step 3: Implement minimal sort change**

In `ShowSortOption`, remove:

```swift
case popular = "popularity_desc"
```

Remove the matching `case .popular: return "Popular"` branch.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /private/tmp/laughtrack-ios-show-standout/ios && swift test --filter SearchRootViewTests/searchRootModelUsesUnifiedSearchState`

Expected: PASS.

### Task 2: Expose Internal Show Popularity Score

**Files:**
- Modify: `apps/web/objects/class/show/show.interface.ts`
- Modify: `apps/web/lib/data/show/search/findShowsWithCount.ts`
- Modify: `ios/Sources/LaughTrackAPIClient/openapi.json`
- Modify: `ios/Sources/LaughTrackAPIClient/GeneratedSources/Types.swift`
- Test: `apps/web/app/api/v1/shows/search/route.test.ts`

- [ ] **Step 1: Write failing API route test**

In the route test fixture show, include:

```ts
popularityScore: 42,
```

Add assertion:

```ts
expect(body.data[0].popularityScore).toBe(42);
```

- [ ] **Step 2: Run route test to verify it fails**

Run: `cd /private/tmp/laughtrack-ios-show-standout/apps/web && npx vitest run app/api/v1/shows/search/route.test.ts`

Expected: FAIL or compile failure because `ShowDTO` does not expose `popularityScore` in the mapped route shape.

- [ ] **Step 3: Implement API field mapping**

In `ShowDTO`, add:

```ts
popularityScore?: number | null;
```

In `mapShowToDTO`, add:

```ts
popularityScore: show.popularity,
```

In `openapi.json`, add this property under `components.schemas.Show.properties`:

```json
"popularityScore": { "type": ["number", "null"] }
```

In generated Swift `Components.Schemas.Show`, add optional `popularityScore: Swift.Double?`, init parameter defaulting to nil, assignment, and `CodingKeys.case popularityScore`.

- [ ] **Step 4: Run route test to verify it passes**

Run: `cd /private/tmp/laughtrack-ios-show-standout/apps/web && npx vitest run app/api/v1/shows/search/route.test.ts`

Expected: PASS.

### Task 3: Compute One Standout Show

**Files:**
- Modify: `ios/Sources/LaughTrackApp/Search/Views/ShowsListView.swift`
- Test: `ios/Tests/LaughTrackTests/ShowsListViewPresentationTests.swift`

- [ ] **Step 1: Write failing helper tests**

Add tests for `ShowsListStandout.resolveID(in:)`:

```swift
@Test("standout resolver picks the single highest positive popularity score")
func standoutResolverPicksSingleHighestPositiveScore() {
    let shows = [
        makeShow(id: 1, popularityScore: 0.2),
        makeShow(id: 2, popularityScore: 0.9),
        makeShow(id: 3, popularityScore: 0.4),
    ]
    #expect(ShowsListStandout.resolveID(in: shows) == 2)
}

@Test("standout resolver returns nil when there is no clear positive winner")
func standoutResolverReturnsNilWithoutClearPositiveWinner() {
    #expect(ShowsListStandout.resolveID(in: [
        makeShow(id: 1, popularityScore: nil),
        makeShow(id: 2, popularityScore: 0),
    ]) == nil)
    #expect(ShowsListStandout.resolveID(in: [
        makeShow(id: 1, popularityScore: 0.8),
        makeShow(id: 2, popularityScore: 0.8),
    ]) == nil)
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /private/tmp/laughtrack-ios-show-standout/ios && swift test --filter ShowsListViewPresentationTests`

Expected: FAIL because `ShowsListStandout` does not exist.

- [ ] **Step 3: Implement resolver**

Create `enum ShowsListStandout` in `ShowsListView.swift` with:

```swift
static func resolveID(in shows: [Components.Schemas.Show]) -> Int? {
    let scored = shows.compactMap { show -> (id: Int, score: Double)? in
        guard let score = show.popularityScore, score > 0 else { return nil }
        return (show.id, score)
    }
    guard let best = scored.max(by: { $0.score < $1.score }) else { return nil }
    let topCount = scored.filter { $0.score == best.score }.count
    return topCount == 1 ? best.id : nil
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /private/tmp/laughtrack-ios-show-standout/ios && swift test --filter ShowsListViewPresentationTests`

Expected: PASS.

### Task 4: Render Premium Compact Ticket for Standout

**Files:**
- Modify: `ios/Sources/LaughTrackApp/Components/ShowRow.swift`
- Modify: `ios/Sources/LaughTrackApp/Search/Views/ShowsListView.swift`
- Test: `ios/Tests/LaughTrackTests/ShowRowTests.swift`
- Test: `ios/Tests/LaughTrackTests/ShowsListViewPresentationTests.swift`

- [ ] **Step 1: Write failing source-level tests**

Update `ShowRowTests.showRowExposesCompactPaperTicketPresentationForHomeRails()` to expect:

```swift
#expect(source.contains("case compactTicketProminent"))
#expect(source.contains("private var ticketEdgeAccent"))
```

Update `ShowsListViewPresentationTests.showSearchResultsUseCompactTicketRowPresentation()` to expect:

```swift
#expect(rowBlock.contains("let standoutShowID = ShowsListStandout.resolveID(in: result.items)"))
#expect(rowBlock.contains("show.id == standoutShowID ? .compactTicketProminent : .compactTicket"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /private/tmp/laughtrack-ios-show-standout/ios && swift test --filter ShowRowTests/showRowExposesCompactPaperTicketPresentationForHomeRails --filter ShowsListViewPresentationTests/showSearchResultsUseCompactTicketRowPresentation`

Expected: FAIL because the new presentation and list wiring do not exist.

- [ ] **Step 3: Implement premium ticket rendering**

Add `case compactTicketProminent` to `ShowRowPresentation`.

Update all presentation switches so `.compactTicketProminent` mostly shares `.compactTicket` values, with richer paper, border, stub, accent, and shadow. Add `ticketEdgeAccent` and overlay it only for `.compactTicketProminent`.

In `ShowsListView`, compute:

```swift
let standoutShowID = ShowsListStandout.resolveID(in: result.items)
```

Pass:

```swift
presentation: show.id == standoutShowID ? .compactTicketProminent : .compactTicket
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /private/tmp/laughtrack-ios-show-standout/ios && swift test --filter ShowRowTests/showRowExposesCompactPaperTicketPresentationForHomeRails --filter ShowsListViewPresentationTests`

Expected: PASS.

### Task 5: Final Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run focused iOS tests**

Run: `cd /private/tmp/laughtrack-ios-show-standout/ios && swift test --filter SearchRootViewTests --filter ShowsListViewPresentationTests --filter ShowRowTests`

Expected: PASS.

- [ ] **Step 2: Run focused web API test**

Run: `cd /private/tmp/laughtrack-ios-show-standout/apps/web && npx vitest run app/api/v1/shows/search/route.test.ts`

Expected: PASS.

- [ ] **Step 3: Check OpenAPI drift if generator dependencies are available**

Run: `cd /private/tmp/laughtrack-ios-show-standout && ios/bin/check-openapi-regen-drift.sh`

Expected: PASS. If dependency download is blocked, report the exact failure and the manually updated generated-field scope.

- [ ] **Step 4: Review diff**

Run: `git -C /private/tmp/laughtrack-ios-show-standout diff --stat && git -C /private/tmp/laughtrack-ios-show-standout diff -- ios/Sources/LaughTrackApp/Search/Models/SearchOptions.swift ios/Sources/LaughTrackApp/Search/Views/ShowsListView.swift ios/Sources/LaughTrackApp/Components/ShowRow.swift apps/web/lib/data/show/search/findShowsWithCount.ts apps/web/objects/class/show/show.interface.ts ios/Sources/LaughTrackAPIClient/openapi.json ios/Sources/LaughTrackAPIClient/GeneratedSources/Types.swift`

Expected: Diff only covers the spec, plan, API field, sort removal, standout resolver, and premium ticket presentation.
