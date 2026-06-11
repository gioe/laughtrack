/**
 * @vitest-environment happy-dom
 */
import React from "react";
import {
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ClubDetailHeader from "./index";
import type { ClubDTO } from "@/objects/class/club/club.interface";

vi.mock("next/image", () => ({
    default: ({
        alt,
        src,
        className,
        onLoad,
    }: {
        alt: string;
        src: string;
        className?: string;
        onLoad?: React.ReactEventHandler<HTMLImageElement>;
    }) => <img alt={alt} src={src} className={className} onLoad={onLoad} />,
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

vi.mock("@/hooks", async () => {
    const { mockUseMotionProps } = await import("@/test/motionProps");
    return { useMotionProps: mockUseMotionProps };
});

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
        // Detail heroes now use the iOS marquee square-poster crop.
        expect(image.className).toContain("object-cover");
    });

    it("letterboxes very wide images inside the square marquee poster", async () => {
        render(
            <ClubDetailHeader
                club={{
                    ...baseClub,
                    heroUrl: "https://cdn.example.com/wide-logo.jpg",
                }}
            />,
        );

        const image = screen.getByAltText("Comedy Cellar");
        Object.defineProperty(image, "naturalWidth", {
            configurable: true,
            value: 1200,
        });
        Object.defineProperty(image, "naturalHeight", {
            configurable: true,
            value: 500,
        });
        fireEvent.load(image);

        await waitFor(() => {
            const loadedImage = screen.getByAltText("Comedy Cellar");
            expect(loadedImage.className).toContain("object-contain");
            expect(loadedImage.className).not.toContain("object-cover");
        });
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

    it("renders the marquee fallback without an image when both are empty", () => {
        const { container } = render(<ClubDetailHeader club={baseClub} />);

        expect(screen.queryByAltText("Comedy Cellar")).toBeNull();
        expect(screen.getByTestId("marquee-poster-fallback")).toBeTruthy();
        expect(screen.getByTestId("marquee-poster-frame").className).toContain(
            "border-dashed",
        );
        // Name still renders above the square poster.
        expect(screen.getByText("Comedy Cellar")).toBeTruthy();
        expect(container.textContent).toContain("New York, NY");
    });
});

describe("ClubDetailHeader description", () => {
    afterEach(cleanup);

    it("renders the club description paragraph inside the hero block", () => {
        render(
            <ClubDetailHeader
                club={{
                    ...baseClub,
                    description:
                        "Legendary West Village club hosting nightly stand-up showcases.",
                }}
            />,
        );

        expect(
            screen.getByText(
                "Legendary West Village club hosting nightly stand-up showcases.",
            ),
        ).toBeTruthy();
    });

    it("omits the description paragraph when the club has no description", () => {
        render(<ClubDetailHeader club={{ ...baseClub, description: "" }} />);

        expect(
            screen.queryByText(
                "Legendary West Village club hosting nightly stand-up showcases.",
            ),
        ).toBeNull();
    });
});
