# Discover Inline Location Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an inline Discover location prompt that lets users set or change nearby recommendations without visiting Profile.

**Architecture:** `HomeView` resolves the existing `NearbyLocationController` and passes it to `HomeDiscoverHeader`. The header owns a `SettingsNearbyPreferenceModel` for shared ZIP/current-location editing and presents a compact sheet. Rails continue observing `NearbyPreferenceStore`, so updates reload existing content.

**Tech Stack:** SwiftUI, LaughTrackCore nearby preference/controller types, Swift Testing.

---

### Task 1: Add Home Header Coverage

**Files:**
- Modify: `ios/Tests/LaughTrackTests/HomeContentSectionTests.swift`

- [ ] **Step 1: Write the failing source-shape test**

Add expectations to the home source test for `HomeDiscoverHeader(nearbyLocationController:)`, `SettingsNearbyPreferenceModel`, `HomeLocationPrompt`, and `HomeLocationEditorSheet`.

- [ ] **Step 2: Run the test**

Run: `cd ios && swift test --filter HomeContentSectionTests`
Expected: fail before implementation because the new symbols are absent.

### Task 2: Implement Inline Location Prompt

**Files:**
- Modify: `ios/Sources/LaughTrackApp/Home/Views/HomeView.swift`
- Modify: `ios/Sources/LaughTrackApp/ContentView.swift`

- [ ] **Step 1: Wire the shared controller**

Resolve `NearbyLocationController` in `HomeView` and pass it into `HomeDiscoverHeader`.

- [ ] **Step 2: Replace passive subtitle with an inline prompt**

`HomeDiscoverHeader` should keep the title and render a button-style `HomeLocationPrompt` showing unset and set states.

- [ ] **Step 3: Add the sheet**

Add `HomeLocationEditorSheet` backed by `SettingsNearbyPreferenceModel`, with manual ZIP, distance picker, use current location, clear, status messages, and permission Settings action.

- [ ] **Step 4: Run tests and simulator build**

Run: `cd ios && swift test`
Run simulator build/run for visual verification.
