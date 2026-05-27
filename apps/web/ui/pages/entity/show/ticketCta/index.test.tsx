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

    it("records detail CTA ticket clicks without preventing the outbound link", () => {
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

        expect(link.getAttribute("href")).toBe("https://example.com/tickets");
        expect(trackTicketClick).toHaveBeenCalledWith({
            showId: 42,
            clubId: 24,
            destinationUrl: "https://example.com/tickets",
            sourceSurface: "show_detail",
        });
    });
});
