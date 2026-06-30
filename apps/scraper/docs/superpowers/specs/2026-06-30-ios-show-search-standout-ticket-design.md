# iOS Show Search Standout Ticket Design

## Goal

Show search results should make the strongest result visually legible without exposing
popularity as a user-facing concept. A user should be able to scan a result list and
notice which show appears most worth considering, while still understanding the list
as practical show results ordered by date, price, or other visible filters.

## Product Decisions

- Remove popularity as a visible sort option for iOS show search.
- Keep popularity as an internal ranking signal only.
- Highlight exactly one show among the currently visible or loaded search results.
- Do not render popularity scores, meters, ranks, or labels.
- Do not use the word "popularity" in user-facing show-search UI.
- If there is no clear standout, render all rows with the normal compact ticket
  treatment.

The selected visual direction is the "premium ticket" treatment: the standout row is
still the same ticket component, but the ticket stock appears more valuable through
subtle material changes.

## Standout Selection

`ShowsListView` should determine the standout show from the current loaded result
items. The standout is the show with the highest internal popularity score.

The first implementation should be conservative:

- Promote a show only when it has a positive numeric popularity score.
- Promote no row when all loaded items have missing, null, zero, or tied top scores.
- Compute against the current loaded result set, including items already fetched by
  pagination.
- Recompute when filters, dates, location, search text, sort, or loaded pages change.

This keeps the highlight local to what the user can see or has loaded. It avoids a
page where no visible row is special because the true best match is hidden on a later
page.

## UI Design

Extend `ShowRow` with a compact-ticket prominence variant used only by show search.
The prominent row keeps the same structure, date stub, content, tap target, and row
height behavior as the existing compact ticket row.

Prominence should be conveyed through ticket material:

- Slightly stronger outer border.
- Warmer/richer ticket paper or gradient.
- Warmer date stub treatment.
- Subtle vertical edge stripe on the body side of the ticket.
- Slightly stronger shadow/depth.
- Optional title weight increase if it remains visually restrained.

The row must not add a separate badge, meter, score, rank, or explanatory label. The
standout should feel like a premium ticket, not a separate component inserted into
the row.

## Sorting Changes

`ShowSortOption` should no longer expose `.popular` / `popularity_desc` in the iOS
show-search picker. Existing deep links or cached state that contain popularity sort
values should be handled safely by mapping them to the default visible show sort,
currently earliest/date ascending.

Backend search can continue to understand existing `popularity_*` raw values for
backward compatibility, but iOS should not offer them as user choices.

## Data Flow

The show payload already includes `socialData` and lineup popularity data in related
contexts, while the web search select includes show `popularity`. The implementation
should first verify which score is actually present in the iOS show-search response.
If show-level popularity is not generated into the Swift `Show` schema, add the
smallest API/OpenAPI/client-generation change needed to expose an internal numeric
score for the iOS client.

Preferred client shape:

1. `ShowsListView` receives `result.items`.
2. A pure helper computes `standoutShowID` from those items.
3. The `ForEach` passes `.compactTicketProminent` or equivalent only when
   `show.id == standoutShowID`.
4. `ShowRow` remains responsible only for rendering the requested presentation.

This keeps ranking policy outside the reusable row component.

## Accessibility

Do not add an accessibility label that says "popular", "best", or "ranked". The
standout is an ambient visual affordance, not a semantic status that changes the
meaning of the show. Existing row labels and navigation behavior should remain
unchanged.

The prominent treatment must still meet contrast expectations for title, metadata,
date, time, and price text.

## Tests

Add focused tests for:

- iOS show sort options no longer include the popularity sort.
- Show-search request defaults and reset behavior use a visible non-popularity sort.
- The standout helper returns the single highest positive score.
- The helper returns no standout for missing scores, all-zero scores, or tied top
  scores.
- `ShowsListView` passes the prominent compact-ticket presentation only to the
  standout row.
- `ShowRow` source or snapshot-style tests cover the prominent compact-ticket
  material tokens without adding visible labels, meters, or ranks.

Existing tests for comedian/club popularity sorts should remain unchanged unless
they specifically exercise show-search behavior.

## Out of Scope

- Web show-search UI changes.
- Admin popularity displays.
- Changing the underlying popularity formula.
- Reordering the result list around the standout.
- Showing more than one premium row.
- Explaining the standout treatment in onboarding or helper text.
