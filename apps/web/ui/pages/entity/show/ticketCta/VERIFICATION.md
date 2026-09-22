# Ticket CTA verification (TASK-4037)

Ticket inventory and destination availability are separate states. The presenter
uses the shared HTTP(S) URL validator also used by the public show API, trying
live ticket rows in order before the show-page fallback. Ended shows take
precedence, then explicit sold-out inventory, then unavailable destinations.

## Visual review

Reviewed the real component with compiled project Tailwind CSS and the app font
at 390px and 1280px. All twelve isolated static renders had no horizontal overflow
or clipped actions/text. This checks component layout, not full-page hydration.

| State | Ticket summary | Action |
| --- | --- | --- |
| Available | Known price | Buy tickets |
| Explicitly sold out | Sold Out | None |
| Missing destination | Ticket link unavailable | None |
| Unknown price, valid destination | Price unavailable with explanation button | Buy tickets |
| Ended | This show has ended. | None |
| Open mic, valid destination | RSVP | RSVP |

Unknown-price text wraps cleanly on phone. The missing-link state uses neutral
text rather than the red sold-out treatment. Automated coverage additionally
checks open mics without destinations, malformed/unsafe URLs, fallback selection,
ended precedence and discovery attribution.

## Automated checks

Run from apps/web:

```sh
npx vitest run ui/pages/entity/show/ticketCta/index.test.tsx 'app/api/v1/shows/[id]/route.test.ts'
```

All 41 tests passed. Before the fix, seven newly added missing/invalid-destination
cases failed while the original ten CTA cases passed. The existing price-dialog
interaction test continues to pass.
