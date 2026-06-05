import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, it, expect, vi, beforeEach } from "vitest";

const mocks = vi.hoisted(() => ({
    auth: vi.fn(),
    cookies: vi.fn(),
    getTrendingComedians: vi.fn(),
    getClubs: vi.fn(),
    getComediansByZip: vi.fn(),
    getShowsTonight: vi.fn(),
    getShowsNearZip: vi.fn(),
    getTrendingShowsThisWeek: vi.fn(),
    getHeroContext: vi.fn(),
    getFavoriteComedianShows: vi.fn(),
}));

vi.mock("../auth", () => ({
    auth: mocks.auth,
}));

vi.mock("next/headers", () => ({
    cookies: mocks.cookies,
}));

vi.mock("next/cache", () => ({
    unstable_cache: (fn: unknown) => fn,
}));

vi.mock("@/lib/data/home/getTrendingComedians", () => ({
    getTrendingComedians: mocks.getTrendingComedians,
}));
vi.mock("@/lib/data/home/getClubs", () => ({
    getClubs: mocks.getClubs,
}));
vi.mock("@/lib/data/home/getComediansByZip", () => ({
    getComediansByZip: mocks.getComediansByZip,
}));
vi.mock("@/lib/data/home/getShowsTonight", () => ({
    getShowsTonight: mocks.getShowsTonight,
}));
vi.mock("@/lib/data/home/getShowsNearZip", () => ({
    getShowsNearZip: mocks.getShowsNearZip,
}));
vi.mock("@/lib/data/home/getTrendingShowsThisWeek", () => ({
    getTrendingShowsThisWeek: mocks.getTrendingShowsThisWeek,
}));
vi.mock("@/lib/data/home/getHeroContext", () => ({
    getHeroContext: mocks.getHeroContext,
}));
vi.mock("@/lib/data/home/getFavoriteComedianShows", () => ({
    getFavoriteComedianShows: mocks.getFavoriteComedianShows,
}));

vi.mock("@/ui/pages/home/hero", () => ({
    default: () => <section data-testid="home-hero" />,
}));
vi.mock("@/ui/pages/home/comedians", () => ({
    default: () => <section data-testid="trending-comedians" />,
}));
vi.mock("@/ui/pages/home/clubs", () => ({
    default: () => <section data-testid="trending-clubs" />,
}));
vi.mock("@/ui/pages/home/shows", () => ({
    default: ({
        title,
        testId,
        seeAllHref,
        shows,
    }: {
        title: string;
        testId?: string;
        seeAllHref: string;
        shows: unknown[];
    }) => (
        <section
            data-testid={testId ?? title}
            data-href={seeAllHref}
            data-count={shows.length}
        >
            {title}
        </section>
    ),
}));
vi.mock("@/ui/pages/home/footer", () => ({
    default: () => <footer data-testid="home-footer" />,
}));
vi.mock("@/ui/components/JsonLd", () => ({
    default: () => null,
}));
vi.mock("@/util/jsonLd", () => ({
    buildWebSiteJsonLd: vi.fn(() => ({})),
}));
vi.mock("./page.fixture", () => ({
    default: () => <main data-testid="fixture-home" />,
}));

import HomePage from "./page";

function renderHomePage() {
    return HomePage().then((element) => renderToStaticMarkup(element));
}

function makeShow(id: number) {
    return {
        id,
        name: `Show ${id}`,
        date: new Date("2026-06-01T20:00:00.000Z"),
        imageUrl: `https://cdn.example.com/show-${id}.jpg`,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    mocks.cookies.mockResolvedValue({ get: vi.fn() });
    mocks.getTrendingComedians.mockResolvedValue([]);
    mocks.getClubs.mockResolvedValue([]);
    mocks.getComediansByZip.mockResolvedValue([]);
    mocks.getShowsTonight.mockResolvedValue([]);
    mocks.getShowsNearZip.mockResolvedValue([]);
    mocks.getTrendingShowsThisWeek.mockResolvedValue([]);
    mocks.getHeroContext.mockResolvedValue({
        city: null,
        state: null,
        zipCode: null,
    });
    mocks.getFavoriteComedianShows.mockResolvedValue([]);
});

describe("HomePage favorite comedian rail", () => {
    it("scopes shows tonight to the resolved profile ZIP", async () => {
        mocks.auth.mockResolvedValue({
            profile: { id: "profile-1", zipCode: "10801" },
        });
        mocks.getHeroContext.mockResolvedValue({
            city: "New Rochelle",
            state: "NY",
            zipCode: "10801",
        });

        await renderHomePage();

        expect(mocks.getShowsTonight).toHaveBeenCalledWith(
            "UTC",
            "10801",
            expect.any(Number),
        );
    });

    it("uses a 25-mile home radius for nearby profile ZIP sections", async () => {
        mocks.auth.mockResolvedValue({
            profile: { id: "profile-1", zipCode: "10801" },
        });
        mocks.getHeroContext.mockResolvedValue({
            city: "New Rochelle",
            state: "NY",
            zipCode: "10801",
        });

        await renderHomePage();

        expect(mocks.getShowsTonight).toHaveBeenCalledWith("UTC", "10801", 25);
        expect(mocks.getShowsNearZip).toHaveBeenCalledWith("10801", 25);
        expect(mocks.getComediansByZip).toHaveBeenCalledWith("10801", 25, {
            sortBy: "upcomingShows",
        });
    });

    it("renders extra nearby shows in one Nearby Shows rail instead of More Near You", async () => {
        mocks.auth.mockResolvedValue({
            profile: { id: "profile-1", zipCode: "10801" },
        });
        mocks.getHeroContext.mockResolvedValue({
            city: "New Rochelle",
            state: "NY",
            zipCode: "10801",
        });
        mocks.getShowsNearZip.mockResolvedValue(
            Array.from({ length: 8 }, (_, index) => makeShow(index + 1)),
        );

        const markup = await renderHomePage();

        expect(markup).toContain("Nearby Shows");
        expect(markup).toContain('data-count="8"');
        expect(markup).toContain(
            'data-href="/show/search?zip=10801&amp;distance=25"',
        );
        expect(markup).not.toContain("More Near You");
    });

    it("renders the personalized rail above trending comedians for signed-in users with favorite shows", async () => {
        mocks.auth.mockResolvedValue({
            profile: { id: "profile-1", zipCode: null },
        });
        mocks.getFavoriteComedianShows.mockResolvedValue([
            {
                id: 1,
                name: "Favorite Comic Night",
                date: new Date("2026-06-01T20:00:00.000Z"),
                imageUrl: "https://cdn.example.com/show.jpg",
            },
        ]);

        const markup = await renderHomePage();

        expect(markup).toContain('data-testid="favorite-comedian-shows"');
        expect(markup).toContain("Your favorites are touring");
        expect(markup.indexOf("Your favorites are touring")).toBeLessThan(
            markup.indexOf('data-testid="trending-comedians"'),
        );
    });

    it("does not query or render the personalized rail for signed-out users", async () => {
        mocks.auth.mockResolvedValue(null);

        const markup = await renderHomePage();

        expect(mocks.getFavoriteComedianShows).not.toHaveBeenCalled();
        expect(markup).not.toContain("Your favorites are touring");
    });

    it("hides the personalized rail when the signed-in user has no favorite shows", async () => {
        mocks.auth.mockResolvedValue({
            profile: { id: "profile-1", zipCode: null },
        });
        mocks.getFavoriteComedianShows.mockResolvedValue([]);

        const markup = await renderHomePage();

        expect(mocks.getFavoriteComedianShows).toHaveBeenCalledWith(
            "profile-1",
        );
        expect(markup).not.toContain("Your favorites are touring");
    });
});
