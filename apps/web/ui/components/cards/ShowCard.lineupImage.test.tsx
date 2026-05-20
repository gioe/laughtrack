/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ShowCard from "./show";
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

vi.mock("framer-motion", () => ({
    motion: {
        article: ({
            children,
            className,
        }: {
            children: React.ReactNode;
            className?: string;
        }) => <article className={className}>{children}</article>,
        div: ({
            children,
            className,
        }: {
            children: React.ReactNode;
            className?: string;
        }) => <div className={className}>{children}</div>,
    },
}));

vi.mock("@/hooks", () => ({
    useMotionProps: () => ({
        mv: (value: unknown) => value,
        mp: (value: unknown) => value,
        prefersReducedMotion: true,
    }),
}));

vi.mock("@/hooks/useFavorite", () => ({
    useFavorite: () => ({
        isFavorite: false,
        handleFavoriteClick: () => Promise.resolve(),
        isAuthenticated: false,
    }),
}));

vi.mock("@/ui/components/cards/show/header", () => ({
    default: () => <div data-testid="show-card-header" />,
}));

const baseShow: ShowDTO = {
    id: 42,
    clubID: 24,
    date: "2026-04-28T20:00:00Z" as never as Date,
    name: "Late Show",
    clubName: "The Copper Room",
    address: "123 Main St",
    imageUrl: "https://cdn.example.com/copper-room.jpg",
    lineup: [],
    tickets: [],
    timezone: "America/New_York",
};

afterEach(() => {
    cleanup();
});

describe("ShowCard lineup imagery", () => {
    it("renders at least one <img> for the lineup when lineup is non-empty", () => {
        const showWithLineup: ShowDTO = {
            ...baseShow,
            lineup: [
                {
                    id: 1,
                    uuid: "uuid-1",
                    name: "Headliner Hannah",
                    imageUrl: "https://cdn.example.com/hannah.jpg",
                    hasImage: true,
                },
            ],
        };

        render(<ShowCard show={showWithLineup} />);

        const lineupImages = screen.getAllByAltText("Headliner Hannah");
        expect(lineupImages.length).toBeGreaterThanOrEqual(1);
        expect(lineupImages[0].getAttribute("src")).toBe(
            "https://cdn.example.com/hannah.jpg",
        );
    });
});
