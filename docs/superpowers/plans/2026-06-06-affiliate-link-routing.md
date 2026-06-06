# Affiliate Link Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route web ticket CTAs through a first-party affiliate-aware outbound flow that redirects safely and records attribution.

**Architecture:** Add pure routing helpers in `apps/web/lib/affiliate`, a Next.js outbound redirect route under `apps/web/app/api/v1/tickets/out`, a small client URL builder in `apps/web/util`, and a Prisma migration adding attribution columns to `ticket_purchase_click_events`. Update existing ticket CTA components to use the outbound URL for href and tracking destination.

**Tech Stack:** Next.js route handlers, Prisma, Vitest, React Testing Library, TypeScript.

---

### Task 1: Pure Affiliate Router

**Files:**
- Create: `apps/web/lib/affiliate/affiliateRouting.ts`
- Test: `apps/web/lib/affiliate/affiliateRouting.test.ts`

- [ ] Write tests for supported configured provider, supported unconfigured provider fallback, unsupported direct venue fallback, and malformed URL rejection.
- [ ] Run `cd apps/web && npx vitest run lib/affiliate/affiliateRouting.test.ts` and confirm it fails because the module does not exist.
- [ ] Implement `resolveAffiliateDestination(input)` with provider detection by hostname and no hardcoded active affiliate ids.
- [ ] Re-run the focused routing test and confirm it passes.

### Task 2: Attribution Metadata and Outbound Route

**Files:**
- Create: `apps/web/app/api/v1/tickets/out/route.ts`
- Create: `apps/web/lib/affiliate/affiliateClickTracking.test.ts`
- Modify: `apps/web/app/api/v1/ticket-clicks/route.ts`
- Modify: `apps/web/prisma/schema.prisma`
- Create: `apps/web/prisma/migrations/20260606122000_add_affiliate_click_metadata/migration.sql`

- [ ] Write route tests that call `/api/v1/tickets/out` with a valid show/club/url/surface and assert 302 redirect plus persisted provider, destination, routed destination, and fallback status.
- [ ] Run `cd apps/web && npx vitest run lib/affiliate/affiliateClickTracking.test.ts` and confirm it fails because the route or fields do not exist.
- [ ] Add nullable Prisma fields: `destinationProvider`, `routedDestinationUrl`, `affiliateApplied`, and `fallbackReason`.
- [ ] Add the matching SQL migration using lowercase `ticket_purchase_click_events`.
- [ ] Implement shared click creation so both the legacy POST route and outbound route can write the extended metadata.
- [ ] Re-run the focused attribution test and confirm it passes.

### Task 3: CTA Integration

**Files:**
- Create: `apps/web/util/ticketOutboundLink.ts`
- Modify: `apps/web/ui/components/cards/show/index.tsx`
- Modify: `apps/web/ui/components/cards/show/compact/index.tsx`
- Modify: `apps/web/ui/pages/entity/show/ticketCta/index.tsx`
- Test: existing CTA tests for those three components

- [ ] Update component tests to expect `/api/v1/tickets/out?...` hrefs while verifying the original destination is still tracked.
- [ ] Run the focused CTA command and confirm the expected failures.
- [ ] Implement the outbound URL builder and update all three CTA components.
- [ ] Re-run the focused CTA command and confirm it passes.

### Task 4: Verification and Closeout

**Files:**
- All files changed above

- [ ] Run `cd apps/web && npx vitest run lib/affiliate/affiliateRouting.test.ts lib/affiliate/affiliateClickTracking.test.ts ui/components/cards/show/index.test.tsx ui/components/cards/show/compact/index.test.tsx ui/pages/entity/show/ticketCta/index.test.tsx`.
- [ ] Run `cd apps/web && npm run type-check`.
- [ ] Commit criteria in focused groups with `tusk commit --criteria`.
