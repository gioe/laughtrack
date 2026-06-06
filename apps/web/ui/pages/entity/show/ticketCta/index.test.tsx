/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ShowTicketCta from "./index";
import type { ShowDetailDTO } from "@/lib/data/show/detail/interface";
import { trackTicketClick } from "@/util/ticketClickTracking";

vi.mock("next/link", () => ({
    default: ({
        children,
        href,
        className,
        ...props
    }: {
        children: React.ReactNode;
        href: string;
        className?: string;
    }) => (
        <a href={href} className={className} {...props}>
            {children}
        </a>
    ),
}));

vi.mock("@/hooks", () => ({
    useDialogKeyboard: () => {},
}));

vi.mock("@/util/ticketClickTracking", () => ({
    trackTicketClick: vi.fn(() => Promise.resolve()),
}));

const baseShow: ShowDetailDTO = {
    id: 42,
    clubId: 24,
    date: "2026-04-28T20:00:00Z" as never as Date,
    name: "Late Show",
    clubName: "The Copper Room",
    address: "123 Main St",
    imageUrl: "https://cdn.example.com/copper-room.jpg",
    lineup: [],
    tickets: [],
    timezone: "America/New_York",
    showPageUrl: "https://example.com/show",
};

afterEach(() => {
    cleanup();
    vi.clearAllMocks();
});

describe("ShowTicketCta", () => {
    it("keeps unknown-priced available tickets as Get Tickets and explains unavailable pricing", () => {
        render(
            <ShowTicketCta
                isPast={false}
                show={{
                    ...baseShow,
                    tickets: [
                        {
                            price: null,
                            purchaseUrl: "https://example.com/tickets",
                            soldOut: false,
                            type: "General admission",
                        },
                    ],
                }}
            />,
        );

        expect(
            screen.getByRole("link", { name: /get tickets for late show/i })
                .textContent,
        ).toContain("Get Tickets");
        expect(screen.queryByText("Free")).toBeNull();

        fireEvent.click(
            screen.getByRole("button", {
                name: /why is the price unavailable/i,
            }),
        );

        expect(
            screen.getByRole("dialog", { name: "Price unavailable" })
                .textContent,
        ).toContain("The venue has not made this ticket price available yet.");
    });

    it("renders the RSVP variant for open-mic shows: no price, RSVP copy, original target preserved in outbound URL", () => {
        render(
            <ShowTicketCta
                isPast={false}
                isOpenMic
                show={{
                    ...baseShow,
                    tickets: [
                        {
                            price: 0,
                            purchaseUrl: "https://example.com/openmic",
                            soldOut: false,
                            type: "RSVP",
                        },
                    ],
                }}
            />,
        );

        const link = screen.getByRole("link", {
            name: /rsvp for late show/i,
        });
        expect(link.textContent).toContain("RSVP");
        expect(link.textContent).not.toContain("Free");
        expect(link.textContent).not.toContain("$");
        const outbound = new URL(
            link.getAttribute("href") ?? "",
            "http://localhost",
        );
        expect(outbound.pathname).toBe("/api/v1/tickets/out");
        expect(outbound.searchParams.get("url")).toBe(
            "https://example.com/openmic",
        );
        expect(
            screen.queryByRole("button", {
                name: /why is the price unavailable/i,
            }),
        ).toBeNull();
    });

    it("routes detail CTA ticket clicks through the outbound link without client-side duplicate tracking", () => {
        render(
            <ShowTicketCta
                isPast={false}
                show={{
                    ...baseShow,
                    tickets: [
                        {
                            price: 24,
                            purchaseUrl: "https://example.com/tickets",
                            soldOut: false,
                            type: "General admission",
                        },
                    ],
                }}
            />,
        );

        const link = screen.getByRole("link", {
            name: /get tickets for late show/i,
        });
        link.addEventListener("click", (event) => event.preventDefault());
        fireEvent.click(link);

        const href = link.getAttribute("href");
        expect(href).toContain("/api/v1/tickets/out?");
        const outbound = new URL(href ?? "", "http://localhost");
        expect(outbound.searchParams.get("showId")).toBe("42");
        expect(outbound.searchParams.get("clubId")).toBe("24");
        expect(outbound.searchParams.get("surface")).toBe("show_detail");
        expect(outbound.searchParams.get("url")).toBe(
            "https://example.com/tickets",
        );
        expect(trackTicketClick).not.toHaveBeenCalled();
    });
});
