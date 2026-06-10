/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ClubDetailHeader from "./index";
import type { ClubDTO } from "@/objects/class/club/club.interface";

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
    motion: new Proxy(
        {},
        {
            get:
                (_target: object, tag: string) =>
                ({
                    children,
                    className,
                }: {
                    children?: React.ReactNode;
                    className?: string;
                }) =>
                    React.createElement(tag, { className }, children),
        },
    ),
}));

vi.mock("@/hooks", () => ({
    useMotionProps: () => ({
        mv: (value: unknown) => value,
        mt: (value: unknown) => value,
        prefersReducedMotion: true,
    }),
}));

vi.mock("../social", () => ({
    default: () => null,
}));

vi.mock("@/ui/pages/entity/club/chainLocations", () => ({
    default: () => null,
}));

const baseClub: ClubDTO = {
    id: 7,
    name: "Comedy Cellar",
    imageUrl: "",
    heroUrl: "",
    address: "117 MacDougal St",
    city: "New York",
    state: "NY",
    zipCode: "10012",
};

describe("ClubDetailHeader hero image", () => {
    afterEach(cleanup);

    it("renders heroUrl when present", () => {
        render(
            <ClubDetailHeader
                club={{
                    ...baseClub,
                    heroUrl: "https://cdn.example.com/hero.jpg",
                    imageUrl: "https://cdn.example.com/logo.jpg",
                }}
            />,
        );

        const image = screen.getByAltText("Comedy Cellar");
        expect(image.getAttribute("src")).toBe(
            "https://cdn.example.com/hero.jpg",
        );
    });

    it("falls back to imageUrl when heroUrl is empty", () => {
        render(
            <ClubDetailHeader
                club={{
                    ...baseClub,
                    heroUrl: "",
                    imageUrl: "https://cdn.example.com/logo.jpg",
                }}
            />,
        );

        const image = screen.getByAltText("Comedy Cellar");
        expect(image.getAttribute("src")).toBe(
            "https://cdn.example.com/logo.jpg",
        );
    });

    it("falls back to imageUrl when heroUrl is the placeholder", () => {
        render(
            <ClubDetailHeader
                club={{
                    ...baseClub,
                    heroUrl: "/placeholders/club-placeholder.svg",
                    imageUrl: "https://cdn.example.com/logo.jpg",
                }}
            />,
        );

        const image = screen.getByAltText("Comedy Cellar");
        expect(image.getAttribute("src")).toBe(
            "https://cdn.example.com/logo.jpg",
        );
    });

    it("renders the gradient fallback without an image when both are empty", () => {
        const { container } = render(<ClubDetailHeader club={baseClub} />);

        expect(screen.queryByAltText("Comedy Cellar")).toBeNull();
        expect(container.querySelector(".bg-gradient-to-br")).not.toBeNull();
        // Name overlay still renders on the gradient
        expect(screen.getByText("Comedy Cellar")).toBeTruthy();
    });
});
