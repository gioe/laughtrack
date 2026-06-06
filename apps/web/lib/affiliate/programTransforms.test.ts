import { describe, expect, it } from "vitest";
import {
    type AffiliateProvider,
    type AffiliateRules,
    resolveAffiliateDestination,
} from "./affiliateRouting";

const QUERY_RULES: AffiliateRules = {
    ticketmaster: { type: "query", queryParam: "camefrom", value: "TM_LT" },
    eventbrite: { type: "query", queryParam: "aff", value: "EB_LT" },
    viator: {
        type: "query",
        queryParam: "pid",
        value: "V_PID",
        extraParams: { mcid: "V_MCID" },
    },
};

const REDIRECT_RULES: AffiliateRules = {
    seatgeek: {
        type: "redirect",
        baseUrl: "https://seatgeek.test/click",
        urlParam: "u",
    },
    tickpick: {
        type: "redirect",
        baseUrl: "https://tickpick.test/click",
        urlParam: "url",
    },
    vivid_seats: {
        type: "redirect",
        baseUrl: "https://vivid.test/click?campaign=laughtrack",
        urlParam: "u",
    },
    stubhub: {
        type: "redirect",
        baseUrl: "https://stubhub.test/click",
        urlParam: "u",
    },
    ticketnetwork: {
        type: "redirect",
        baseUrl: "https://ticketnetwork.test/click",
        urlParam: "u",
    },
    fever: {
        type: "redirect",
        baseUrl: "https://fever.test/click",
        urlParam: "u",
    },
    gametime: {
        type: "redirect",
        baseUrl: "https://gametime.test/click",
        urlParam: "u",
    },
};

describe("priority affiliate program transforms", () => {
    it.each([
        [
            "ticketmaster",
            "https://www.ticketmaster.com/event/abc123?brand=test",
            "https://www.ticketmaster.com/event/abc123?brand=test&camefrom=TM_LT",
        ],
        [
            "eventbrite",
            "https://www.eventbrite.com/e/comedy-night-tickets-123",
            "https://www.eventbrite.com/e/comedy-night-tickets-123?aff=EB_LT",
        ],
        [
            "viator",
            "https://www.viator.com/tours/New-York-City/show/d687-12345P1",
            "https://www.viator.com/tours/New-York-City/show/d687-12345P1?pid=V_PID&mcid=V_MCID",
        ],
    ] satisfies Array<[AffiliateProvider, string, string]>)(
        "adds query tracking for %s",
        (provider, destinationUrl, routedUrl) => {
            const result = resolveAffiliateDestination({
                destinationUrl,
                rules: QUERY_RULES,
            });

            expect(result).toMatchObject({
                ok: true,
                provider,
                originalUrl: destinationUrl,
                routedUrl,
                affiliateApplied: true,
                fallbackReason: null,
            });
        },
    );

    it.each([
        [
            "seatgeek",
            "https://seatgeek.com/venues/comedy-cellar/tickets",
            "https://seatgeek.test/click?u=https%3A%2F%2Fseatgeek.com%2Fvenues%2Fcomedy-cellar%2Ftickets",
        ],
        [
            "tickpick",
            "https://www.tickpick.com/buy-comedy-tickets/123",
            "https://tickpick.test/click?url=https%3A%2F%2Fwww.tickpick.com%2Fbuy-comedy-tickets%2F123",
        ],
        [
            "vivid_seats",
            "https://www.vividseats.com/comedy/comedian-tickets.html",
            "https://vivid.test/click?campaign=laughtrack&u=https%3A%2F%2Fwww.vividseats.com%2Fcomedy%2Fcomedian-tickets.html",
        ],
        [
            "stubhub",
            "https://www.stubhub.com/comedy-tickets/category/123",
            "https://stubhub.test/click?u=https%3A%2F%2Fwww.stubhub.com%2Fcomedy-tickets%2Fcategory%2F123",
        ],
        [
            "ticketnetwork",
            "https://www.ticketnetwork.com/en/concerts/tickets/comedy/123",
            "https://ticketnetwork.test/click?u=https%3A%2F%2Fwww.ticketnetwork.com%2Fen%2Fconcerts%2Ftickets%2Fcomedy%2F123",
        ],
        [
            "fever",
            "https://feverup.com/m/12345",
            "https://fever.test/click?u=https%3A%2F%2Ffeverup.com%2Fm%2F12345",
        ],
        [
            "gametime",
            "https://gametime.co/comedy/123",
            "https://gametime.test/click?u=https%3A%2F%2Fgametime.co%2Fcomedy%2F123",
        ],
    ] satisfies Array<[AffiliateProvider, string, string]>)(
        "wraps %s destinations in a configured redirect",
        (provider, destinationUrl, routedUrl) => {
            const result = resolveAffiliateDestination({
                destinationUrl,
                rules: REDIRECT_RULES,
            });

            expect(result).toMatchObject({
                ok: true,
                provider,
                originalUrl: destinationUrl,
                routedUrl,
                affiliateApplied: true,
                fallbackReason: null,
            });
        },
    );
});
