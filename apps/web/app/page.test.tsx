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
vi.mock("@/ui/pages/home/comedians-near-you", () => ({
    default: () => <section data-testid="comedians-near-you" />,
}));
vi.mock("@/ui/pages/home/clubs", () => ({
    default: () => <section data-testid="trending-clubs" />,
}));
vi.mock("@/ui/pages/home/shows", () => ({
    default: ({ title, testId }: { title: string; testId?: string }) => (
        <section data-testid={testId ?? title}>{title}</section>
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
