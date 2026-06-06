import { describe, expect, it } from "vitest";
import {
    type AffiliateProvider,
    resolveAffiliateDestination,
} from "./affiliateRouting";

describe("priority affiliate program fallbacks", () => {
    it.each([
        ["ticketmaster", "https://www.ticketmaster.com/event/abc123"],
        ["eventbrite", "https://www.eventbrite.com/e/comedy-tickets-123"],
        ["seatgeek", "https://seatgeek.com/comedy/123"],
        ["tickpick", "https://www.tickpick.com/comedy-tickets/123"],
        ["vivid_seats", "https://www.vividseats.com/comedy/comedian.html"],
        ["stubhub", "https://www.stubhub.com/comedy-tickets/category/123"],
        [
            "ticketnetwork",
            "https://www.ticketnetwork.com/en/concerts/tickets/comedy/123",
        ],
        ["fever", "https://feverup.com/m/12345"],
        ["gametime", "https://gametime.co/comedy/123"],
        ["viator", "https://www.viator.com/tours/New-York-City/d687-123"],
        ["tixr", "https://www.tixr.com/groups/supernova/events"],
        ["seatengine", "https://venue.seatengine.com/events"],
    ] satisfies Array<[AffiliateProvider, string]>)(
        "keeps the original %s destination when no rule is active",
        (provider, destinationUrl) => {
            expect(resolveAffiliateDestination({ destinationUrl })).toEqual({
                ok: true,
                provider,
                originalUrl: destinationUrl,
                routedUrl: destinationUrl,
                affiliateApplied: false,
                fallbackReason: "no_affiliate_rule",
            });
        },
    );

    it("keeps direct venue links working without affiliate rules", () => {
        const destinationUrl = "https://venue.example.com/shows/late-show";

        expect(resolveAffiliateDestination({ destinationUrl })).toEqual({
            ok: true,
            provider: "direct_venue",
            originalUrl: destinationUrl,
            routedUrl: destinationUrl,
            affiliateApplied: false,
            fallbackReason: "direct_venue",
        });
    });

    it("falls back to the original URL when a configured redirect is invalid", () => {
        const destinationUrl = "https://seatgeek.com/comedy/123";

        expect(
            resolveAffiliateDestination({
                destinationUrl,
                rules: {
                    seatgeek: {
                        type: "redirect",
                        baseUrl: "not a url",
                        urlParam: "u",
                    },
                },
            }),
        ).toEqual({
            ok: true,
            provider: "seatgeek",
            originalUrl: destinationUrl,
            routedUrl: destinationUrl,
            affiliateApplied: false,
            fallbackReason: "invalid_affiliate_rule",
        });
    });

    it("falls back to the original URL when a configured redirect uses a non-http protocol", () => {
        const destinationUrl = "https://seatgeek.com/comedy/123";

        expect(
            resolveAffiliateDestination({
                destinationUrl,
                rules: {
                    seatgeek: {
                        type: "redirect",
                        baseUrl: "javascript:alert(1)",
                        urlParam: "u",
                    },
                },
            }),
        ).toEqual({
            ok: true,
            provider: "seatgeek",
            originalUrl: destinationUrl,
            routedUrl: destinationUrl,
            affiliateApplied: false,
            fallbackReason: "invalid_affiliate_rule",
        });
    });
});
