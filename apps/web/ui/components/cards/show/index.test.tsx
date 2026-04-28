/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ShowCard from "./index";
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
    },
}));

vi.mock("@/hooks", () => ({
    useMotionProps: () => ({
        mv: (value: unknown) => value,
        mp: (value: unknown) => value,
        prefersReducedMotion: true,
    }),
}));

vi.mock("@/ui/components/cards/show/header", () => ({
    default: () => <div data-testid="show-card-header" />,
}));

vi.mock("@/ui/components/lineup", () => ({
    default: () => <div data-testid="lineup-grid" />,
}));

afterEach(() => {
    cleanup();
});

const baseShow: ShowDTO = {
    id: 42,
    date: "2026-04-28T20:00:00Z" as unknown as Date,
    name: "Late Show",
    clubName: "The Copper Room",
    address: "123 Main St",
    imageUrl: "https://cdn.example.com/copper-room.jpg",
    lineup: [],
    tickets: [],
    timezone: "America/New_York",
};

describe("ShowCard", () => {
    it("keeps rendering the lineup grid in the default context", () => {
        render(<ShowCard show={baseShow} />);

        expect(screen.getAllByTestId("lineup-grid")).toHaveLength(2);
        expect(
            screen.queryByAltText("The Copper Room venue artwork"),
        ).toBeNull();
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
});
