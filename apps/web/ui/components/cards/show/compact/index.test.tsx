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
    it("contains the club thumbnail so wide venue artwork is not cropped", () => {
        const { container } = render(<CompactShowCard show={baseShow} />);

        const image = container.querySelector('img[alt="The Copper Room"]');
        expect(image?.className).toContain("object-contain");
        expect(image?.className).not.toContain("object-cover");
    });

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

    it("routes compact-card ticket clicks through the outbound link without client-side duplicate tracking", () => {
        render(<CompactShowCard show={baseShow} />);

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
        expect(outbound.searchParams.get("surface")).toBe("compact_show_card");
        expect(outbound.searchParams.get("url")).toBe(
            "https://example.com/tickets",
        );
        expect(trackTicketClick).not.toHaveBeenCalled();
    });
});
