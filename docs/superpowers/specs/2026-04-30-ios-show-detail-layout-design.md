# iOS Show Detail Layout Design

## Context

The current iOS show detail screen uses the shared `DetailHero`, but its content below the hero is less polished than the comedian and club detail pages. It also repeats key details between the hero badges and the first content card, which makes the page feel heavier than it needs to.

## Direction

Use the event-first layout direction:

- Keep the full-bleed `DetailHero` treatment so show detail visually matches comedian and club detail.
- Make the hero responsible for identity only: show date/time and show name.
- Remove venue, ticket price, distance, and room badges from the hero.
- Put the operational details in the first card as a compact fact grid.
- Keep the ticket CTA directly after the fact grid so the primary action stays above lineup and related shows.
- Keep lineup and related shows in the existing card pattern used elsewhere in detail pages.

## Hero

The show hero should display:

- Date/time as the subtitle.
- Show name as the title.
- The current show image.

The hero should not display:

- Venue name.
- Ticket price.
- Distance.
- Room.

If a show is sold out, sold-out status belongs in the ticket section and the fact grid, not as a hero badge.

## Event Summary Card

The first card below the hero should be a show summary card with a two-column fact grid where space allows. Each fact should be short and scannable:

- When: concise local date/time label.
- Tickets: lowest available price, free, sold out, or unavailable.
- Venue: club name.
- Room: room name when present.
- Distance: formatted distance when present.
- Address: address when present.

On narrow layouts, the grid can still render as two columns if text fits; otherwise it should degrade cleanly to one column without truncating important values.

## Ticket Section

The ticket section should be visually lighter than the current large accent card. It should include:

- One primary ticket button using the API-provided CTA label.
- A sold-out disabled state when `cta.isSoldOut` is true.
- Individual ticket options when available, showing ticket type and price.
- Fallback show-page button only when it differs from the primary CTA URL.

It should avoid descriptive implementation copy such as “Primary and fallback buttons use the same branded language...”.

## Remaining Sections

The lineup section stays below the ticket section:

- Render `ComedianLineupRow` for each lineup item.
- Keep the existing empty state for TBA lineups.

Related shows stay last:

- Use existing `ShowRow` components.
- Keep the muted card tone.

## Testing

Add focused Swift tests for presentation helpers rather than brittle pixel tests:

- Hero badges for show detail should be empty for normal venue/price/distance data.
- Summary facts should include venue and ticket price when present.
- Summary facts should omit empty room/distance/address values.
- Ticket section copy should not include implementation-language subtitle text.

Run the targeted iOS test suite after implementation, then build the app for simulator if the tests pass.
