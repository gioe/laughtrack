# iOS Show Detail Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the iOS show detail screen so it matches the comedian and club detail pages while removing duplicated venue and ticket information from the hero.

**Architecture:** Keep the existing `ShowDetailView` screen and shared `DetailHero`. Add show-specific presentation helpers in `ShowDetailView.swift` so tests can validate the hero badges, summary facts, and ticket copy without brittle UI snapshots.

**Tech Stack:** SwiftUI, Swift Testing, generated `LaughTrackAPIClient` models, existing LaughTrack design tokens/components.

---

### Task 1: Presentation Helpers

**Files:**
- Modify: `ios/Sources/LaughTrackApp/Detail/Views/ShowDetailView.swift`
- Test: `ios/Tests/LaughTrackTests/ShowDetailViewTests.swift`

- [ ] **Step 1: Write failing tests**

Add tests proving show hero badges are empty, summary facts include ticket/venue facts, and empty values are omitted.

- [ ] **Step 2: Run tests to verify failure**

Run: `swift test --filter ShowDetailViewTests`

- [ ] **Step 3: Implement helper types**

Add `ShowDetailPresentation`, `ShowDetailFact`, and ticket-price helpers to `ShowDetailView.swift`.

- [ ] **Step 4: Run tests to verify pass**

Run: `swift test --filter ShowDetailViewTests`

### Task 2: SwiftUI Layout

**Files:**
- Modify: `ios/Sources/LaughTrackApp/Detail/Views/ShowDetailView.swift`

- [ ] **Step 1: Replace hero badges**

Call `DetailHero` with no badges so venue, ticket price, distance, room, and sold-out status are not duplicated in the hero.

- [ ] **Step 2: Add summary card**

Insert a show summary card immediately under the hero using the presentation facts.

- [ ] **Step 3: Simplify ticket section copy**

Make the ticket card visually lighter and remove implementation-language subtitle text.

- [ ] **Step 4: Verify**

Run: `swift test --filter ShowDetailViewTests`, then build/run the simulator target.
