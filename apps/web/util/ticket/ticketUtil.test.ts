import { describe, expect, it } from "vitest";

import { mapTickets } from "./ticketUtil";

describe("mapTickets", () => {
    it("keeps ticket prices numeric for API clients", () => {
        const tickets = mapTickets([
            {
                price: { toNumber: () => 9 },
                purchaseUrl: "https://example.com/tickets",
                type: "General Admission",
                soldOut: false,
            },
        ]);

        expect(tickets[0].price).toBe(9);
        expect(typeof tickets[0].price).toBe("number");
        expect(JSON.parse(JSON.stringify(tickets))[0].price).toBe(9);
    });
});
