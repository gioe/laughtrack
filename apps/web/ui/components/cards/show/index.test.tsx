/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ShowCard from "./index";
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

vi.mock("framer-motion", () => ({
    motion: {
        article: ({
            children,
            className,
        }: {
            children: React.ReactNode;
            className?: string;
        }) => <article className={className}>{children}</article>,
    },
}));

vi.mock("@/hooks", () => ({
    useMotionProps: () => ({
        mv: (value: unknown) => value,
        mp: (value: unknown) => value,
        prefersReducedMotion: true,
    }),
    useDialogKeyboard: () => {},
}));

vi.mock("@/ui/components/cards/show/header", () => ({
    default: () => <div data-testid="show-card-header" />,
}));

vi.mock("@/ui/components/lineup", () => ({
    default: () => <div data-testid="lineup-grid" />,
}));

vi.mock("@/util/ticketClickTracking", () => ({
    trackTicketClick: vi.fn(() => Promise.resolve()),
}));

afterEach(() => {
    cleanup();
    vi.clearAllMocks();
});

const baseShow: ShowDTO = {
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
};

describe("ShowCard", () => {
    it("renders the lineup grid in the default context when lineup is non-empty", () => {
        const showWithLineup: ShowDTO = {
            ...baseShow,
            lineup: [
                {
                    id: 1,
                    uuid: "uuid-1",
                    name: "Headliner",
                    imageUrl: "https://cdn.example.com/headliner.jpg",
                    hasImage: true,
                },
            ],
        };
        render(<ShowCard show={showWithLineup} />);

        expect(screen.getAllByTestId("lineup-grid")).toHaveLength(2);
        expect(
            screen.queryByAltText("The Copper Room venue artwork"),
        ).toBeNull();
    });

    it("falls back to venue artwork in the default context when lineup is empty", () => {
        render(<ShowCard show={baseShow} />);

        expect(screen.queryByTestId("lineup-grid")).toBeNull();
        const artworkImages = screen.getAllByAltText(
            "The Copper Room venue artwork",
        );
        expect(artworkImages).toHaveLength(2);
        expect(artworkImages[0].className).toContain("object-contain");
        expect(artworkImages[0].className).not.toContain("object-cover");
    });

    it("uses venue artwork instead of the lineup grid in comedian detail context", () => {
        render(<ShowCard show={baseShow} context="comedian-detail" />);

        expect(screen.queryByTestId("lineup-grid")).toBeNull();
        const artworkImages = screen.getAllByAltText(
            "The Copper Room venue artwork",
        );
        expect(artworkImages).toHaveLength(2);
        expect(artworkImages[0].getAttribute("src")).toBe(
            "https://cdn.example.com/copper-room.jpg",
        );
    });

    it("shows sold out when show.soldOut is true even if a ticket row looks available", () => {
        render(
            <ShowCard
                show={{
                    ...baseShow,
                    soldOut: true,
                    tickets: [
                        {
                            price: 30,
                            purchaseUrl: "https://tickets.example.com",
                            type: "General Admission",
                            soldOut: false,
                        },
                    ],
                }}
            />,
        );

        expect(
            screen.getByRole("button", { name: /is sold out/i }).textContent,
        ).toBe("Sold Out");
        expect(screen.queryByRole("link", { name: /get tickets/i })).toBeNull();
    });

    it("shows an info control for unknown-priced available tickets", () => {
        render(
            <ShowCard
                show={{
                    ...baseShow,
                    tickets: [
                        {
                            price: null,
                            purchaseUrl: "https://tickets.example.com",
                            type: "General Admission",
                            soldOut: false,
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

    it("records card ticket clicks without blocking the outbound link", () => {
        render(
            <ShowCard
                show={{
                    ...baseShow,
                    tickets: [
                        {
                            price: 30,
                            purchaseUrl: "https://tickets.example.com",
                            type: "General Admission",
                            soldOut: false,
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

        expect(link.getAttribute("href")).toBe("https://tickets.example.com");
        expect(trackTicketClick).toHaveBeenCalledWith({
            showId: 42,
            clubId: 24,
            destinationUrl: "https://tickets.example.com",
            sourceSurface: "show_card",
        });
    });
});
