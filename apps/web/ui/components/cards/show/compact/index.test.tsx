/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import CompactShowCard from "./index";
import type { ShowDTO } from "@/objects/class/show/show.interface";
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

vi.mock("next/image", () => ({
    default: ({
        alt,
        src,
        className,
    }: {
        alt: string;
        src: string;
        className?: string;
    }) => <img alt={alt} src={src} className={className} />,
}));

vi.mock("@/hooks", () => ({
    useMotionProps: () => ({
        mv: (value: unknown) => value,
        mp: (value: unknown) => value,
        prefersReducedMotion: true,
    }),
    useDialogKeyboard: () => {},
}));

vi.mock("@/util/ticketClickTracking", () => ({
    trackTicketClick: vi.fn(() => Promise.resolve()),
}));

const baseShow: ShowDTO = {
    id: 42,
    clubId: 24,
    date: "2026-04-28T20:00:00Z" as never as Date,
    name: "Late Show",
    clubName: "The Copper Room",
    address: "123 Main St",
    imageUrl: "https://cdn.example.com/copper-room.jpg",
    lineup: [
        {
            name: "Headliner",
            uuid: "headliner",
            id: 7,
            imageUrl: "https://cdn.example.com/headliner.jpg",
            showCount: 10,
        },
    ],
    tickets: [
        {
            price: 24,
            purchaseUrl: "https://example.com/tickets",
            soldOut: false,
            type: "General admission",
        },
    ],
    timezone: "America/New_York",
};

afterEach(() => {
    cleanup();
    vi.clearAllMocks();
});

describe("CompactShowCard", () => {
    it("renders the show name before the club name", () => {
        const { container } = render(<CompactShowCard show={baseShow} />);

        const primary = container.querySelector(
            '[data-testid="compact-show-title"]',
        );
        const secondary = container.querySelector(
            '[data-testid="compact-show-club"]',
        );

        expect(primary?.textContent).toBe("Late Show");
        expect(secondary?.textContent).toBe("The Copper Room");
    });

    it("shows available ticket price", () => {
        render(<CompactShowCard show={baseShow} />);

        expect(screen.getAllByText("$24")).toHaveLength(1);
    });

    it("shows an info control for unknown-priced available tickets", () => {
        render(
            <CompactShowCard
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

    it("records compact-card ticket clicks without blocking the outbound link", () => {
        render(<CompactShowCard show={baseShow} />);

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
            sourceSurface: "compact_show_card",
        });
    });
});
