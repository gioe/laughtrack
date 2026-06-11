/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ShowTicketCta from "./index";
import type { ShowDetailDTO } from "@/lib/data/show/detail/interface";
import { trackTicketClick } from "@/util/ticketClickTracking";
import { isShowPast } from "@/util/dateUtil";

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
    it("renders WHEN, VENUE, and TICKETS as rows of one stub card with the price and a venue link", () => {
        render(
            <ShowTicketCta
                isPast={false}
                show={{
                    ...baseShow,
                    room: "Main Room",
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

        expect(screen.getByText("When")).toBeTruthy();
        expect(screen.getByText("Venue")).toBeTruthy();
        expect(screen.getByText("Tickets")).toBeTruthy();
        // 2026-04-28T20:00:00Z is April 28 in America/New_York.
        expect(screen.getByText(/april 28/i)).toBeTruthy();
        expect(screen.getByText("$24")).toBeTruthy();
        expect(screen.getByText("Main Room · 123 Main St")).toBeTruthy();

        const venueLink = screen.getByRole("link", {
            name: "The Copper Room",
        });
        expect(venueLink.getAttribute("href")).toBe("/club/The Copper Room");
    });

    it("keeps unknown-priced available tickets buyable and explains unavailable pricing", () => {
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
            screen.getByRole("link", { name: /buy tickets for late show/i })
                .textContent,
        ).toContain("Buy tickets");
        expect(screen.getByText("Price unavailable")).toBeTruthy();
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

    it("omits room from the venue sub-line when it duplicates the club name, keeping the address", () => {
        const { unmount } = render(
            <ShowTicketCta
                isPast={false}
                show={{
                    ...baseShow,
                    room: "the copper room",
                }}
            />,
        );

        // Case-insensitive match against clubName: only the address renders.
        expect(screen.getByText("123 Main St")).toBeTruthy();
        expect(screen.queryByText(/the copper room ·/i)).toBeNull();
        // The club-name link above the sub-line is unaffected.
        expect(
            screen.getByRole("link", { name: "The Copper Room" }),
        ).toBeTruthy();
        unmount();

        // A genuinely distinct room still renders alongside the address.
        render(
            <ShowTicketCta
                isPast={false}
                show={{ ...baseShow, room: "Main Room" }}
            />,
        );
        expect(screen.getByText("Main Room · 123 Main St")).toBeTruthy();
    });

    it("falls back to 'This venue' when clubName is missing and omits the VENUE row entirely when no venue data exists", () => {
        const { unmount } = render(
            <ShowTicketCta
                isPast={false}
                show={{ ...baseShow, clubName: undefined }}
            />,
        );

        // Address alone keeps the row, with the non-link fallback value.
        expect(screen.getByText("This venue")).toBeTruthy();
        expect(screen.getByText("123 Main St")).toBeTruthy();
        expect(
            screen.queryByRole("link", { name: "The Copper Room" }),
        ).toBeNull();
        unmount();

        render(
            <ShowTicketCta
                isPast={false}
                show={{
                    ...baseShow,
                    clubName: undefined,
                    address: undefined,
                    room: undefined,
                }}
            />,
        );

        expect(screen.queryByText("Venue")).toBeNull();
        expect(screen.queryByText("This venue")).toBeNull();
        // The rest of the stub still renders.
        expect(screen.getByText("When")).toBeTruthy();
        expect(screen.getByText("Tickets")).toBeTruthy();
    });

    it("renders the ended state inside the stub without a buy pill", () => {
        render(
            <ShowTicketCta
                isPast
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

        expect(screen.getByText("This show has ended.")).toBeTruthy();
        // The stub rows still render, but no outbound CTA does.
        expect(screen.getByText("When")).toBeTruthy();
        expect(screen.queryByRole("link", { name: /buy tickets/i })).toBeNull();
    });

    it("keeps a show inside the live window buyable instead of showing ended copy", () => {
        const now = new Date("2026-05-14T18:00:00Z");
        const halfHourAgo = new Date(now.getTime() - 30 * 60 * 1000);

        render(
            <ShowTicketCta
                isPast={isShowPast(halfHourAgo.toISOString(), now)}
                show={{
                    ...baseShow,
                    date: halfHourAgo.toISOString() as never as Date,
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

        expect(screen.queryByText("This show has ended.")).toBeNull();
        expect(screen.getByText("$24")).toBeTruthy();
        expect(
            screen.getByRole("link", { name: /buy tickets for late show/i }),
        ).toBeTruthy();
    });

    it("renders Sold Out inside the stub when every ticket row is sold out", () => {
        render(
            <ShowTicketCta
                isPast={false}
                show={{
                    ...baseShow,
                    tickets: [
                        {
                            price: 24,
                            purchaseUrl: "https://example.com/tickets",
                            soldOut: true,
                            type: "General admission",
                        },
                    ],
                }}
            />,
        );

        expect(screen.getByText("Sold Out")).toBeTruthy();
        expect(screen.queryByRole("link", { name: /buy tickets/i })).toBeNull();
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
            name: /buy tickets for late show/i,
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
