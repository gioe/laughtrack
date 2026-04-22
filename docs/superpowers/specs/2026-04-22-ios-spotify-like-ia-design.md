# iOS Spotify-Like IA Redesign

Date: 2026-04-22
Status: Approved for planning
Scope: `ios/`

## Summary

LaughTrack's current iOS IA is effectively a single-stack app rooted at `Home`, with dedicated sibling routes for shows, clubs, comedians, and settings. The redesign should move the app closer to Spotify's top-level mental model without copying it blindly.

The chosen direction is:

- Keep `Home` as a discovery and editorial surface.
- Make `Search` the primary operational surface.
- Default `Search` to local-first discovery.
- Let `Search` fan out clearly into `Shows`, `Comedians`, and `Clubs`.
- Keep saved content under `Profile` rather than introducing a Spotify-style `Library` tab.

The result should feel structurally closer to Spotify while remaining honest about LaughTrack's product: local comedy discovery with explicit entity-type pivots.

## Product Decisions

### Confirmed choices

- The Spotify behavior to borrow most aggressively is the search fan-out model.
- `Search` should default to a nearby/locality-first experience.
- After a user chooses a location or grants nearby access, the search screen should update in place rather than redirecting to a separate hub.
- The search experience should be moderately close to Spotify, but with stronger visible pivots for `Shows`, `Comedians`, and `Clubs`.
- `Home` should remain a separate editorial and discovery surface.
- Saved and followed content should live under `Profile` or settings, not in a top-level `Library` tab.

### Chosen shell

Recommended top-level shell:

- `Home`
- `Search`
- `Activity`
- `Profile`

`Activity` may ship initially as a thin destination if the underlying feature set is still shallow. The shell choice reserves space for user-specific alerts and reminders without forcing those concerns into `Home` or `Profile`.

## IA Thesis

The app should separate inspirational browsing from intentional retrieval:

- `Home` answers: "What comedy around me is worth noticing?"
- `Search` answers: "Help me find a specific kind of comedy near this place, date, or entity."
- Detail screens answer: "Tell me everything about this show, club, or comedian."
- `Profile` answers: "What have I saved, and how is my app configured?"

The current IA blurs these jobs by making `Home` both a discovery feed and an index of separate search destinations. The redesign should make `Home` more curated and make `Search` the single place where result exploration happens.

## Information Architecture

### 1. Home

Purpose:

- Editorial and local discovery surface
- Personalized re-entry point
- Lightweight browsing and inspiration

Expected content types:

- Featured nearby shows
- Tonight / this week local shelves
- Venue spotlights
- Comedians performing near saved location
- Follow-based recommendations such as "Because you follow ..."
- Return-path shelves such as recent or resumed exploration

Rules:

- `Home` should not keep separate entry cards for shows, clubs, and comedians search.
- `Home` can deep-link into `Search` with a seeded state.
- `Home` should feel curated rather than utilitarian.

### 2. Search

Purpose:

- The primary working surface for discovery with intent
- A single adaptive place for locality, query, and entity filtering

Core behavior:

- Default to nearby or saved location context
- Show one primary search field at the top
- Show a compact locality/context row under it
- Show explicit entity pivots: `Shows`, `Comedians`, `Clubs`
- Update results in place as the user changes query, location, date shortcuts, or entity pivot

Search content model:

- Before or during query entry, surface recent searches, suggested queries, and local shortcut chips
- Keep visible pivots so the user always understands whether they are browsing shows, comedians, or clubs
- Allow mixed suggestions in the early state, but maintain a clearly selected active pivot
- Preserve result-to-detail navigation for show, comedian, and club detail screens

Principle:

Spotify can hide taxonomy because its content domain is broad but uniform. LaughTrack cannot. The search surface must preserve clear content-type control.

### 3. Activity

Purpose:

- Notifications
- Saved alerts
- Reminder-related activity
- Possibly recent user-specific events over time

Constraints:

- Do not overdesign this before the underlying product surface exists.
- The initial version can be thin if needed.
- The tab exists to avoid pushing user-alert concerns into unrelated destinations.

### 4. Profile

Purpose:

- Account and auth
- Nearby preferences and location controls
- Favorites and follows
- Settings subpages

Rules:

- Nearby settings should no longer define the whole settings mental model for the app.
- Saved content should live here unless a future product phase justifies a top-level `Library`.

## Navigation Architecture

### Current state

Current root routes:

- `home`
- `settings`
- `showsSearch`
- `clubsSearch`
- `comediansSearch`
- detail routes for shows, comedians, and clubs

This creates a home-first stack with multiple sibling search screens.

### Proposed state

Use a tab-based shell with independent navigation stacks per top-level destination:

- `Home` stack
- `Search` stack
- `Activity` stack
- `Profile` stack

Routing changes:

- Replace dedicated `showsSearch`, `clubsSearch`, and `comediansSearch` root routes with a single `search` root route.
- Keep `showDetail(Int)`, `comedianDetail(Int)`, and `clubDetail(Int)` as pushed detail destinations.
- Move settings-related screens under the `Profile` stack.

Why this matters:

- Each tab can preserve its own state and navigation history.
- Search state becomes internal state of one destination rather than being spread across multiple routes.
- The app shell becomes closer to Spotify's mental model without requiring a fake `Library` tab.

## Search State Model

The new `Search` destination should own a single search state object or equivalent model that includes:

- active locality context
- active text query
- active entity pivot (`Shows`, `Comedians`, `Clubs`)
- optional date/time shortcut selection such as `Tonight` or `This Week`
- optional distance or other lightweight filters
- recent search state for empty or pre-query mode

Expected behavior:

- switching pivots updates the result mode in place
- changing location or distance updates the same screen rather than navigating away
- `Home` deep links can seed `Search` with a preselected pivot and query context

## Deep Links and Cross-Surface Behavior

`Home` should be able to send the user into `Search` with explicit state, for example:

- nearby shows tonight
- a particular comedian query
- a venue-focused local browse state

This means cross-surface navigation should pass an explicit search seed rather than depending on multiple dedicated route types.

## UI Boundaries

### Home UI

Should feel:

- visual
- shelf-based
- editorial
- local and alive

Should avoid:

- acting like a settings launcher
- duplicating the full search toolset
- presenting separate cards whose only job is "open the shows search screen"

### Search UI

Should feel:

- direct
- adaptive
- locality-aware
- clearly segmented by entity type

Should avoid:

- hidden taxonomy
- routing the user to different screens for small mode changes
- behaving like a generic filter form

## Error Handling and Edge States

### No location available

- Show a friendly default search state with ZIP or locality entry
- Keep the user on `Search`
- Do not force a separate setup flow unless absolutely necessary

### Empty results

- Keep the user in the same search context
- Offer query relaxation or pivot switching
- Offer nearby/time adjustments before pushing the user elsewhere

### Signed-out user

- Browsing and search should remain usable
- Profile-owned features can gate saved items, follows, and account-specific controls

### Shallow Activity surface

- If notifications or reminders are not mature enough, the `Activity` tab should still have a coherent minimal state rather than placeholder clutter

## Migration Strategy

Phase the redesign to reduce risk:

1. Introduce the new tab shell and route ownership.
2. Consolidate the three dedicated search screens into one `Search` destination with internal pivots.
3. Rework `Home` to remove explicit search-entry cards and become a curated discovery surface.
4. Move settings, favorites, and nearby preferences into `Profile`.
5. Expand `Activity` once the product model justifies it.

This order isolates the highest-risk architectural change first: route ownership and state lifetime.

## Testing Strategy

The redesign needs coverage at three levels:

### Navigation tests

- tab selection and root rendering
- per-tab navigation stack preservation
- detail push behavior from `Home` and `Search`
- seeded deep links from `Home` into `Search`

### Search behavior tests

- pivot switching updates content in place
- location context changes do not navigate away
- query changes preserve the active pivot
- empty, loading, and signed-out states remain coherent

### Regression tests

- existing detail screens still render correctly
- auth restoration still works with the new shell
- favorites and nearby preferences still appear in the correct destination after moving under `Profile`

## Non-Goals

- Reproducing Spotify's visual brand directly
- Introducing a top-level `Library` tab in this phase
- Redesigning the backend API contract as part of the IA decision alone
- Overbuilding `Activity` before notifications and reminders are product-ready

## Recommended Approach

Proceed with Option A, the strong search-centered shell:

- `Home` remains editorial and discovery-led
- `Search` becomes the app's primary operational surface
- Search is local-first by default
- explicit entity pivots replace separate search destinations
- `Profile` owns saved content and settings

This is the cleanest way to achieve the requested Spotify-like feel while keeping the product legible as a local comedy app rather than a music app imitation.
