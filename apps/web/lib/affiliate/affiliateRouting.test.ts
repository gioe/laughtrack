import { describe, expect, it } from "vitest";
import { resolveAffiliateDestination } from "./affiliateRouting";

describe("resolveAffiliateDestination", () => {
    it("applies the configured affiliate strategy for a supported provider", () => {
        const result = resolveAffiliateDestination({
            destinationUrl: "https://www.ticketmaster.com/event/abc123?brand=test",
            rules: {
                ticketmaster: {
                    queryParam: "camefrom",
                    value: "CFC_LAUGHTRACK",
                },
            },
        });

        expect(result).toEqual({
            ok: true,
            provider: "ticketmaster",
            originalUrl: "https://www.ticketmaster.com/event/abc123?brand=test",
            routedUrl:
                "https://www.ticketmaster.com/event/abc123?brand=test&camefrom=CFC_LAUGHTRACK",
            affiliateApplied: true,
            fallbackReason: null,
        });
    });

    it("keeps supported providers as fallback links when no affiliate rule exists", () => {
        const result = resolveAffiliateDestination({
            destinationUrl: "https://www.eventbrite.com/e/comedy-night-tickets-123",
        });

        expect(result).toEqual({
            ok: true,
            provider: "eventbrite",
            originalUrl:
                "https://www.eventbrite.com/e/comedy-night-tickets-123",
            routedUrl: "https://www.eventbrite.com/e/comedy-night-tickets-123",
            affiliateApplied: false,
            fallbackReason: "no_affiliate_rule",
        });
    });

    it("keeps direct venue URLs as non-affiliate fallbacks", () => {
        const result = resolveAffiliateDestination({
            destinationUrl: "https://venue.example.com/shows/late-show",
        });

        expect(result).toEqual({
            ok: true,
            provider: "direct_venue",
            originalUrl: "https://venue.example.com/shows/late-show",
            routedUrl: "https://venue.example.com/shows/late-show",
            affiliateApplied: false,
            fallbackReason: "direct_venue",
        });
    });

    it.each([
        "https://theannoyance.thundertix.com/orders/new?performance_id=314159",
        "https://tickets.chanhassendt.com/Online/default.asp?BOparam::WScontent::loadArticle::permalink=stevierays",
        "https://www.flapperscomedy.com/site/shows.php?shid=123456",
    ])("keeps direct venue query-string identity intact for %s", (url) => {
        const result = resolveAffiliateDestination({ destinationUrl: url });

        expect(result).toEqual({
            ok: true,
            provider: "direct_venue",
            originalUrl: url,
            routedUrl: url,
            affiliateApplied: false,
            fallbackReason: "direct_venue",
        });
    });

    it("rejects malformed and non-http destinations", () => {
        expect(
            resolveAffiliateDestination({ destinationUrl: "not a url" }),
        ).toEqual({
            ok: false,
            provider: "malformed",
            originalUrl: null,
            routedUrl: null,
            affiliateApplied: false,
            fallbackReason: "malformed_url",
        });

        expect(
            resolveAffiliateDestination({
                destinationUrl: "javascript:alert(1)",
            }),
        ).toEqual({
            ok: false,
            provider: "malformed",
            originalUrl: null,
            routedUrl: null,
            affiliateApplied: false,
            fallbackReason: "unsupported_protocol",
        });
    });
});
