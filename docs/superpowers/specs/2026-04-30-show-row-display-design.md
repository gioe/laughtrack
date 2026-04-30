# Show Row Display Design

## Goal

Show rows and compact show cards should identify the actual show first. The artwork may still come from the most popular comedian in the lineup, but the row title must use `show.name` whenever it is present. Ticket price should be visible on list rows/cards because it is a key decision point.

## Display Rules

- Primary title: `show.name`, trimmed. If absent, fall back to `Untitled show`.
- Artwork: keep the current featured-lineup-comedian image selection where it exists; fall back to existing venue/ticket placeholder behavior.
- Subtitle: club name remains secondary.
- Metadata: date/time remains visible; distance and sold-out state remain visible when present.
- Price: show the formatted available-ticket price string when at least one non-sold-out ticket has a price. Use the existing ticket formatting conventions: single price, free, or range.
- Missing price: omit the price label rather than showing a fake value. Sold-out still displays as sold out.

## Web Scope

Update show-list cards so the visual hierarchy matches the rule:

- `ShowCardHeader` should render `show.name` as the primary heading and club name as secondary text.
- `CompactShowCard` should render `show.name` as the primary text and club name underneath.
- Existing ticket data stays in the `ShowDTO.tickets` contract; no API shape change is required.
- Existing CTA behavior stays unchanged.

## iOS Scope

Update native `ShowRow`:

- `ShowRow.title(for:)` returns `show.name` instead of the featured comedian.
- `ShowRow.artworkImageURL(for:)` continues choosing the effective highest-show-count lineup comedian image.
- Add a row metadata price label using the show tickets already available in the generated API model.
- Keep sold-out, date, and distance metadata.

## Testing

- iOS: update `ShowRowTests` so title selection verifies show-name priority, artwork still verifies featured-comedian image selection, and price formatting covers single price, range, free, missing price, and sold out.
- Web: update component tests or add focused tests for show card/header display so show name is primary and ticket price remains visible.

## Out Of Scope

- No scraper changes.
- No API schema changes.
- No show detail page redesign.
- No changes to how the featured lineup comedian is selected for artwork.
