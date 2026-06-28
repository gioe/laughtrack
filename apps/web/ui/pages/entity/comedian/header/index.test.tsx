/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ComedianDetailHeader from "./index";
import { useFavorite } from "@/hooks/useFavorite";
import type { ComedianDTO } from "@/objects/class/comedian/comedian.interface";

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
    AnimatePresence: ({ children }: { children?: React.ReactNode }) => (
        <>{children}</>
    ),
}));

vi.mock("@/hooks", () => ({
    MOTION_TAP_SCALE: 0.98,
    useMotionProps: () => ({
        springs: {
            tapFeedback: { duration: 0 },
            contentEntrance: { duration: 0 },
            emphasis: { duration: 0 },
        },
        mv: (value: unknown, fallback?: unknown) => value ?? fallback,
        mp: (value: unknown) => value,
        prefersReducedMotion: true,
    }),
}));

vi.mock("@/hooks/useFavorite", () => ({
    useFavorite: vi.fn(),
}));

const mockUseFavorite = vi.mocked(useFavorite);

const baseComedian: ComedianDTO = {
    id: 12,
    uuid: "comedian-12",
    name: "Taylor Tomlinson",
    imageUrl: "https://cdn.example.com/taylor.jpg",
    hasImage: true,
    showCount: 3,
    socialData: {
        id: 1,
        instagramFollowers: null,
        tiktokFollowers: null,
        youtubeFollowers: null,
        instagramAccount: null,
        tiktokAccount: null,
        youtubeAccount: null,
        website: null,
        popularity: null,
        linktree: null,
    },
    dates: [],
};

beforeEach(() => {
    mockUseFavorite.mockReturnValue({
        isFavorite: false,
        handleFavoriteClick: vi.fn(),
        isAuthenticated: true,
    });
});

afterEach(() => {
    cleanup();
    vi.clearAllMocks();
});

describe("ComedianDetailHeader", () => {
    it("renders the comedian hero as an uppercase marquee poster", () => {
        render(<ComedianDetailHeader comedian={baseComedian} />);

        const title = screen.getByRole("heading", { level: 1 });
        expect(title.textContent).toBe("Taylor Tomlinson");
        expect(title.className).toContain("uppercase");
        expect(screen.getByTestId("marquee-poster-frame").className).toContain(
            "border-dashed",
        );
        expect(screen.getByAltText("Taylor Tomlinson").className).toContain(
            "object-cover",
        );
    });

    it("renders the comedian fallback inside the marquee ring without an image", () => {
        render(
            <ComedianDetailHeader
                comedian={{ ...baseComedian, imageUrl: "", hasImage: false }}
            />,
        );

        expect(screen.getByTestId("marquee-poster-fallback")).toBeTruthy();
        expect(screen.queryByAltText("Taylor Tomlinson")).toBeNull();
    });

    it("renders the home city and a linked home club when present", () => {
        render(
            <ComedianDetailHeader
                comedian={{
                    ...baseComedian,
                    homeLocation: {
                        city: "Austin",
                        state: "TX",
                        country: "USA",
                        club: { id: 7, name: "Cap City Comedy Club" },
                    },
                }}
            />,
        );

        expect(screen.getByText("Based in Austin, TX")).toBeTruthy();
        const clubLink = screen.getByLabelText(
            "Home club: Cap City Comedy Club",
        );
        expect(clubLink.getAttribute("href")).toBe(
            "/club/Cap City Comedy Club",
        );
    });

    it("falls back to country as the region when state is null", () => {
        render(
            <ComedianDetailHeader
                comedian={{
                    ...baseComedian,
                    homeLocation: {
                        city: "Toronto",
                        state: null,
                        country: "Canada",
                        club: null,
                    },
                }}
            />,
        );

        expect(screen.getByText("Based in Toronto, Canada")).toBeTruthy();
        expect(screen.queryByText(/Home club:/)).toBeNull();
    });

    it("omits the city pill but keeps the home club when city is null", () => {
        render(
            <ComedianDetailHeader
                comedian={{
                    ...baseComedian,
                    homeLocation: {
                        city: null,
                        state: null,
                        country: null,
                        club: { id: 9, name: "The Stand" },
                    },
                }}
            />,
        );

        expect(screen.queryByText(/Based in/)).toBeNull();
        expect(screen.getByLabelText("Home club: The Stand")).toBeTruthy();
    });

    it("renders no home-location pills when the home location is absent", () => {
        render(<ComedianDetailHeader comedian={baseComedian} />);

        expect(screen.queryByText(/Based in/)).toBeNull();
        expect(screen.queryByText(/Home club:/)).toBeNull();
    });
});
