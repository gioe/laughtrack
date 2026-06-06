# Affiliate Link Routing Design

## Goal

Add a centralized outbound ticket-link flow that can route ticket CTAs through affiliate-aware destinations while preserving direct vendor and venue links when no mapping exists.

## Design

Ticket CTAs should no longer link directly to scraped vendor URLs. They should build a first-party outbound URL containing the show id, club id, source surface, and original destination. The first-party route resolves the destination through a shared affiliate router, records click attribution, and redirects to either the affiliate URL or the original URL.

The affiliate router lives in `apps/web/lib/affiliate/` and is pure TypeScript so it can be tested without Next.js. It identifies known ticketing providers by URL hostname, applies provider-specific affiliate rules only when configured, and returns explicit fallback reasons for unsupported, malformed, and direct venue URLs.

The outbound route lives under `apps/web/app/api/v1/tickets/out/route.ts`. It validates query params, rejects malformed or unsafe destinations, rate-limits public access, verifies the show and club association, records the click event, and responds with a 302 redirect. Existing non-affiliate destinations continue to redirect to their original URL.

Click attribution extends the existing `ticket_purchase_click_events` table with provider, routed destination URL, and fallback status. It continues to avoid raw IP storage and uses the existing profile or opaque anonymous visitor identity behavior.

## Testing

Tests cover pure routing behavior, outbound route attribution, and CTA component hrefs/click behavior. The focused acceptance commands are:

- `cd apps/web && npx vitest run lib/affiliate/affiliateRouting.test.ts`
- `cd apps/web && npx vitest run ui/components/cards/show/index.test.tsx ui/components/cards/show/compact/index.test.tsx ui/pages/entity/show/ticketCta/index.test.tsx`
- `cd apps/web && npx vitest run lib/affiliate/affiliateClickTracking.test.ts`
