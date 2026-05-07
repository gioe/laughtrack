/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import CompactShowCard from "./index";
import type { ShowDTO } from "@/objects/class/show/show.interface";

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
}));

const baseShow: ShowDTO = {
    id: 42,
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
            show_count: 10,
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
});
