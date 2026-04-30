# Show Row Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make show rows/cards title with the actual show name, keep featured-lineup artwork, and expose ticket price in list metadata.

**Architecture:** Keep API contracts unchanged. Update display helpers/components in web and iOS only, reusing existing ticket arrays and price formatting utilities.

**Tech Stack:** SwiftUI, Swift Testing, React/Next.js, Vitest, Testing Library.

---

### Task 1: iOS ShowRow Title And Price

**Files:**
- Modify: `ios/Sources/LaughTrackApp/Components/ShowRow.swift`
- Modify: `ios/Tests/LaughTrackTests/ShowRowTests.swift`

- [ ] Write failing Swift tests that expect `ShowRow.title(for:)` to return `show.name`, featured artwork to remain lineup-based, and price metadata to format single/range/free/missing-price cases.
- [ ] Run `swift test --filter ShowRowTests` and verify the title/price tests fail.
- [ ] Update `ShowRow` so title uses show name, artwork still uses featured lineup comedian, and metadata includes `ShowRow.priceLabel(for:)` before sold-out status.
- [ ] Run `swift test --filter ShowRowTests` and verify it passes.

### Task 2: Web Show Card Hierarchy

**Files:**
- Modify: `apps/web/ui/components/cards/show/header/index.tsx`
- Modify: `apps/web/ui/components/cards/show/compact/index.tsx`
- Add or modify tests near existing show-card tests.

- [ ] Write failing React tests verifying show name is primary, club name is secondary, and price text is visible for available tickets.
- [ ] Run the targeted web tests and verify they fail.
- [ ] Update show card/header rendering to match the approved hierarchy and keep CTA behavior unchanged.
- [ ] Run the targeted web tests and verify they pass.

### Task 3: Final Verification

- [ ] Run `swift test --filter ShowRowTests`.
- [ ] Run targeted web tests.
- [ ] Run `git diff --check`.
- [ ] Commit and push the implementation.
