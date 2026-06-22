import { describe, expect, it } from "vitest";
import {
    PRIORITY_AFFILIATE_PROVIDERS,
    resolveAffiliateDestination,
    type AffiliateRules,
} from "./affiliateRouting";

/**
 * TASK-2683 — event affiliate-program expansion evaluation.
 *
 * The expansion beyond the first 10 priority programs evaluated five candidate
 * programs (AXS, TodayTix, Goldstar, TicketSmarter, Ticket Squeeze, SI Tickets).
 * Outcome: NONE were onboarded — see apps/web/docs/affiliate-programs-expansion.md
 * for the per-program viability decisions (program availability, commission
 * model, deep-link support, trust risk) and rationale:
 *   - TodayTix / Goldstar  -> DEFER (legitimate, but low comedy-club inventory
 *     match; revisit if comedy relevance/volume warrants).
 *   - TicketSmarter / SI Tickets / Ticket Squeeze -> REJECT (secondary-resale
 *     markup + consumer-trust risk; contradicts LaughTrack's venue-first value).
 *   - AXS -> DEFER (TASK-2706; ride-along once inventory clears the threshold).
 *
 * These tests lock in the rejection/deferral: every rejected or deferred
 * candidate must (a) be absent from the priority program set and (b) never
 * rewrite an outbound ticket URL — regardless of which existing affiliate
 * rules are active.
 */

// Representative destination URLs for each evaluated-but-not-onboarded program.
const NOT_ONBOARDED_DESTINATIONS: Array<[string, string]> = [
    ["axs", "https://www.axs.com/events/123456/comedy-tickets"],
    ["todaytix", "https://www.todaytix.com/nyc/shows/12345-comedy"],
    ["goldstar", "https://www.goldstar.com/events/boston-ma/comedy-night"],
    ["ticketsmarter", "https://www.ticketsmarter.com/comedy/tickets"],
    ["ticketsqueeze", "https://www.ticketsqueeze.com/comedy-tickets"],
    ["sitickets", "https://sitickets.com/comedy/event/123"],
];

// A fully-populated rules map simulating a deployment where every onboarded
// program HAS credentials, to prove the not-onboarded candidates still never
// rewrite even when affiliate routing is otherwise fully active.
const ALL_EXISTING_RULES_ACTIVE: AffiliateRules = {
    ticketmaster: { type: "query", queryParam: "camefrom", value: "TEST" },
    eventbrite: { type: "query", queryParam: "aff", value: "TEST" },
    seatgeek: { type: "query", queryParam: "aid", value: "TEST" },
    tickpick: { type: "query", queryParam: "utm_source", value: "TEST" },
    vivid_seats: { type: "query", queryParam: "wsUser", value: "TEST" },
    stubhub: {
        type: "redirect",
        baseUrl: "https://www.awin1.com/cread.php?awinmid=1&awinaffid=2&ued=",
        urlParam: "ued",
    },
    ticketnetwork: { type: "query", queryParam: "aff", value: "TEST" },
    fever: { type: "query", queryParam: "fppc", value: "TEST" },
    gametime: { type: "query", queryParam: "ftm", value: "TEST" },
    viator: { type: "query", queryParam: "pid", value: "TEST" },
};

describe("event affiliate program expansion (TASK-2683)", () => {
    it("did not add any evaluated candidate to the priority program set", () => {
        const providers = PRIORITY_AFFILIATE_PROVIDERS as readonly string[];
        for (const [name] of NOT_ONBOARDED_DESTINATIONS) {
            expect(providers).not.toContain(name);
        }
        // The expansion left the count at the original 10 priority programs.
        expect(PRIORITY_AFFILIATE_PROVIDERS).toHaveLength(10);
    });

    it.each(NOT_ONBOARDED_DESTINATIONS)(
        "never rewrites a %s destination when no rules are active",
        (_name, destinationUrl) => {
            const result = resolveAffiliateDestination({ destinationUrl });
            expect(result.ok).toBe(true);
            if (result.ok) {
                expect(result.affiliateApplied).toBe(false);
                expect(result.routedUrl).toBe(destinationUrl);
                expect(result.provider).toBe("direct_venue");
            }
        },
    );

    it.each(NOT_ONBOARDED_DESTINATIONS)(
        "never rewrites a %s destination even when every onboarded program is active",
        (_name, destinationUrl) => {
            const result = resolveAffiliateDestination({
                destinationUrl,
                rules: ALL_EXISTING_RULES_ACTIVE,
            });
            expect(result.ok).toBe(true);
            if (result.ok) {
                expect(result.affiliateApplied).toBe(false);
                expect(result.routedUrl).toBe(destinationUrl);
            }
        },
    );
});
