import { describe, expect, it } from "vitest";
import { buildTicketOutboundHref } from "./ticketOutboundLink";

describe("buildTicketOutboundHref", () => {
    it("includes an originating discovery impression when provided", () => {
        const impressionId = "00000000-0000-4000-8000-000000000001";
        const href = buildTicketOutboundHref({
            showId: 42,
            clubId: 24,
            destinationUrl: "https://example.com/tickets",
            sourceSurface: "compact_show_card",
            impressionId,
        });

        expect(
            new URL(href, "http://localhost").searchParams.get("impressionId"),
        ).toBe(impressionId);
    });

    it.each([
        [
            "ThunderTix",
            "https://theannoyance.thundertix.com/orders/new?performance_id=314159",
        ],
        [
            "Chanhassen",
            "https://tickets.chanhassendt.com/Online/default.asp?BOparam::WScontent::loadArticle::permalink=stevierays",
        ],
        [
            "Flappers",
            "https://www.flapperscomedy.com/site/shows.php?shid=123456",
        ],
    ])(
        "preserves query-string event identity for %s",
        (_name, destinationUrl) => {
            const href = buildTicketOutboundHref({
                showId: 42,
                clubId: 24,
                destinationUrl,
                sourceSurface: "show_card",
            });

            const parsed = new URL(href, "http://localhost");
            expect(parsed.pathname).toBe("/api/v1/tickets/out");
            expect(parsed.searchParams.get("url")).toBe(destinationUrl);
        },
    );
});
