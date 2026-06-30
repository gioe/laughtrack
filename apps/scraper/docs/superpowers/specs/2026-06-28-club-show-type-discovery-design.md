# Club and Show Type Discovery Design

## Goal

Introduce user-facing discovery and filtering by the kind of programming a venue hosts. Users should be able to find standup-heavy clubs, improv venues, theaters with comedy, mixed comedy venues, and similar categories without forcing every club into a single permanent identity.

## Current State

The database already has `clubs.club_type`, but it is a coarse venue/entity classifier rather than a programming classifier. Current values include `club`, `venue`, `festival`, `producer`, `secret_location`, and `non_comedy`. This field also drives operational behavior such as festival scraping and non-venue row handling, so it should not be overloaded with values like `standup`, `improv`, or `music`.

The `shows` table does not currently store a show type. Show records contain title, description, room, source attribution, lineup, tickets, and tags, but no normalized classification for the type of event.

## Core Decision

Use show-level type as the source of truth for programming, then derive club-level discovery profile fields from the club's shows.

`club_type` answers: what kind of place or entity is this?

`show_type` answers: what kind of event is this?

The user-facing club category should be derived from both. For example, a theater that regularly hosts standup should remain a theater at the venue/entity layer while appearing in comedy discovery through its standup show mix.

## Show Type Taxonomy

Add a nullable `shows.show_type` field with a constrained string taxonomy:

- `standup`
- `improv`
- `sketch`
- `theater`
- `musical_comedy`
- `open_mic`
- `variety`
- `podcast`
- `class_workshop`
- `music`
- `other`
- `unknown`

`unknown` means the system attempted classification but did not have enough evidence. `NULL` means the row predates the feature or has not been classified yet. This distinction supports incremental rollout and backfills.

The initial taxonomy should stay small. New values should be added only when they unlock a real filter, label, or data-quality decision.

## Club Discovery Profile

Add a derived club-level profile for fast filtering. Implement this as a separate summary table because the data is derived and can evolve without making `clubs` carry every future summary field.

Proposed summary shape:

```text
club_discovery_profiles
- club_id
- primary_show_type
- show_type_counts jsonb
- comedy_show_count
- non_comedy_show_count
- mixed_programming boolean
- confidence
- computed_at
```

`primary_show_type` is the dominant show type for the relevant discovery window. `show_type_counts` stores the distribution used to derive that label. `mixed_programming` is true when no single show type dominates enough to describe the club cleanly.

The discovery window should use active/future inventory plus a bounded recent-history fallback. This keeps labels aligned with what users can actually attend while avoiding empty profiles for clubs whose future scrape is temporarily sparse.

## User-Facing Labels

Do not expose raw database values directly as the main user-facing label. Instead derive display labels from `club_type`, `primary_show_type`, and show mix.

Example labels:

- `Comedy club`
- `Standup club`
- `Improv theater`
- `Theater with comedy`
- `Music venue with comedy`
- `Mixed comedy venue`
- `Festival`
- `Producer`

Filters should be based on normalized fields, not display labels.

## Classification Inputs

Classify shows conservatively using deterministic evidence:

- scraper/platform categories when available
- venue-specific scraper knowledge for high-confidence sources
- normalized tags already attached to shows
- title and description keyword rules
- known venue defaults only when the venue is specialized enough to be reliable

Avoid aggressive guessing. Ambiguous rows should be `unknown`, not forced into a category. A weak classifier is worse than no classifier if it causes user-facing filters to hide relevant shows.

## Rollout

1. Add `shows.show_type` and application model support.
2. Update show persistence so `show_type` is inserted and updated through the existing batch upsert path.
3. Add deterministic classification helpers with unit tests.
4. Backfill high-confidence show types first.
5. Add club discovery profile computation.
6. Expose profile fields to web search/filtering.
7. Add UI filters and labels using the derived profile.

The first release can support a narrow useful subset: standup, improv, theater, music, open mic, and unknown. Additional values can be populated later as classifiers improve.

## Filtering Semantics

User-facing filters should have clear semantics:

- Show filters match `shows.show_type`.
- Club filters match derived club profile fields.
- "Standup clubs" should mean clubs with standup as the primary or materially present show type, not necessarily `club_type = club`.
- "Theaters with comedy" should mean `club_type` indicates theater/venue behavior and the profile has comedy-like shows.
- "Hide non-comedy" should exclude clubs with no material comedy-like show inventory, not merely clubs whose `club_type` is not `club`.

Comedy-like show types initially include `standup`, `improv`, `sketch`, `musical_comedy`, `open_mic`, `variety`, and `podcast` when the event context is comedic.

## Profile Thresholds

Use these initial thresholds for `primary_show_type` and `mixed_programming`:

- primary type requires at least 60% of classified shows in the discovery window
- otherwise mark `mixed_programming = true`
- ignore `unknown` rows for percentage calculation unless all rows are unknown

These thresholds should live in code, not in migrations, so they can be adjusted with tests and backfilled summaries can be recomputed after real-world review.

## Non-Goals

This design does not replace existing tags. Tags remain useful for themes, performers, specials, or source-provided labels. `show_type` is a small primary classification, not an open-ended tag system.

This design does not make `club_type` fully user-facing. `club_type` remains an operational venue/entity classifier and should not absorb programming categories.

This design does not require machine-learning classification for the first version. Deterministic classification is sufficient for the initial user-facing filters and easier to audit.

## Testing

Tests should cover:

- show model persistence includes `show_type`
- batch upsert updates `show_type` correctly
- classifier rules for high-confidence title/category cases
- ambiguous shows remain `unknown`
- club profile computation handles mixed venues, unknown-heavy venues, and empty future inventory
- web filters do not rely on display labels

## Risks

The main risk is false confidence. If classifiers over-label theater, music, or variety events as standup, users will see irrelevant inventory. The mitigation is conservative classification, explicit `unknown`, profile confidence, and staged backfills.

Another risk is confusing `club_type` with programming type. Keeping club discovery profile separate prevents operational behavior from changing when user-facing filters evolve.
