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

vi.mock("@/hooks", async () => {
    const { mockUseMotionProps } = await import("@/test/motionProps");
    return {
        useMotionProps: mockUseMotionProps,
        useDialogKeyboard: () => {},
    };
});

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
    it("uses show name as the primary h3 heading and club as secondary text", () => {
        render(<ShowCard show={baseShow} />);

        expect(
            screen.getByRole("heading", { level: 3, name: "Late Show" }),
        ).toBeTruthy();
        expect(
            screen.getAllByText("The Copper Room").length,
        ).toBeGreaterThanOrEqual(1);
    });

    it("shows available ticket price metadata in the header", () => {
        render(
            <ShowCard
                show={{
                    ...baseShow,
                    tickets: [
                        {
                            price: 24,
                            purchaseUrl: "https://example.com/tickets",
                            type: "General admission",
                            soldOut: false,
                        },
                    ],
                }}
            />,
        );

        expect(screen.getAllByText("$24")).toHaveLength(1);
    });

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

    it("routes card ticket clicks through the outbound link without client-side duplicate tracking", () => {
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

        const href = link.getAttribute("href");
        expect(href).toContain("/api/v1/tickets/out?");
        const outbound = new URL(href ?? "", "http://localhost");
        expect(outbound.searchParams.get("showId")).toBe("42");
        expect(outbound.searchParams.get("clubId")).toBe("24");
        expect(outbound.searchParams.get("surface")).toBe("show_card");
        expect(outbound.searchParams.get("url")).toBe(
            "https://tickets.example.com",
        );
        expect(trackTicketClick).not.toHaveBeenCalled();
    });
});

const compactShow: ShowDTO = {
    ...baseShow,
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
};

describe("ShowCard (compact density)", () => {
    it("retains qualified discovery attribution on detail and ticket links", () => {
        const onShowDetail = vi.fn();
        const impressionId = "00000000-0000-4000-8000-000000000001";
        render(
            <ShowCard
                show={compactShow}
                density="compact"
                discoveryAttribution={{
                    impressionId,
                    onShowDetail,
                }}
            />,
        );

        const detailLink = screen.getByRole("link", {
            name: /view details for late show/i,
        });
        expect(
            new URL(
                detailLink.getAttribute("href") ?? "",
                "http://localhost",
            ).searchParams.get("impressionId"),
        ).toBe(impressionId);
        fireEvent.click(detailLink);
        expect(onShowDetail).toHaveBeenCalledOnce();

        const ticketLink = screen.getByRole("link", {
            name: /get tickets for late show/i,
        });
        expect(
            new URL(
                ticketLink.getAttribute("href") ?? "",
                "http://localhost",
            ).searchParams.get("impressionId"),
        ).toBe(impressionId);
    });

    it("contains the club thumbnail so wide venue artwork is not cropped", () => {
        const { container } = render(
            <ShowCard show={compactShow} density="compact" />,
        );

        const image = container.querySelector('img[alt="The Copper Room"]');
        expect(image?.className).toContain("object-contain");
        expect(image?.className).not.toContain("object-cover");
    });

    it("renders the show name before the club name", () => {
        const { container } = render(
            <ShowCard show={compactShow} density="compact" />,
        );

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
        render(<ShowCard show={compactShow} density="compact" />);

        expect(screen.getAllByText("$24")).toHaveLength(1);
    });

    it("shows an info control for unknown-priced available tickets", () => {
        render(
            <ShowCard
                density="compact"
                show={{
                    ...compactShow,
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
        render(<ShowCard show={compactShow} density="compact" />);

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
