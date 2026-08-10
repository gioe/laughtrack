import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    auth: vi.fn(),
    cookies: vi.fn(),
    getTrendingComedians: vi.fn(),
    getClubs: vi.fn(),
    getClubsByZip: vi.fn(),
    getComediansByZip: vi.fn(),
    getShowsTonight: vi.fn(),
    getShowsNearZipWithTelemetry: vi.fn(),
    getTrendingShowsThisWeek: vi.fn(),
    getHeroContext: vi.fn(),
    getFavoriteComedianShows: vi.fn(),
    getDiscoveryRailPolicy: vi.fn(),
    getTouringScarcityRails: vi.fn(),
    getFreshAndRisingRails: vi.fn(),
    getAffinityRails: vi.fn(),
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
vi.mock("@/lib/data/home/getClubsByZip", () => ({
    getClubsByZip: mocks.getClubsByZip,
}));
vi.mock("@/lib/data/home/getComediansByZip", () => ({
    getComediansByZip: mocks.getComediansByZip,
}));
vi.mock("@/lib/data/home/getShowsTonight", () => ({
    getShowsTonight: mocks.getShowsTonight,
}));
vi.mock("@/lib/data/home/getShowsNearZip", () => ({
    getShowsNearZipWithTelemetry: mocks.getShowsNearZipWithTelemetry,
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
vi.mock("@/lib/data/home/getDiscoveryRailPolicy", () => ({
    getDiscoveryRailPolicy: mocks.getDiscoveryRailPolicy,
}));
vi.mock("@/lib/data/home/getTouringScarcityRails", () => ({
    getTouringScarcityRails: mocks.getTouringScarcityRails,
}));
vi.mock("@/lib/data/home/getFreshAndRisingRails", () => ({
    getFreshAndRisingRails: mocks.getFreshAndRisingRails,
}));
vi.mock("@/lib/data/home/getAffinityRails", () => ({
    getAffinityRails: mocks.getAffinityRails,
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
        discoveryPresentation,
    }: {
        title: string;
        testId?: string;
        seeAllHref: string;
        shows: unknown[];
        discoveryPresentation?: {
            policyVersion: string;
            experimentVariant: string;
        };
    }) => (
        <section
            data-testid={testId ?? title}
            data-href={seeAllHref}
            data-count={shows.length}
            data-policy-version={discoveryPresentation?.policyVersion}
            data-experiment-variant={discoveryPresentation?.experimentVariant}
        >
            {title}
        </section>
    ),
}));
vi.mock("@/ui/pages/home/footer", () => ({
    default: () => <footer data-testid="home-footer" />,
}));
vi.mock("@/ui/pages/home/DiscoveryRailPlan", () => ({
    default: ({
        plan,
        fallback,
    }: {
        plan: { platform?: string; policyVersion?: number } | null;
        fallback: React.ReactNode;
    }) => (
        <div
            data-testid="discovery-rail-plan"
            data-platform={plan?.platform}
            data-policy-version={plan?.policyVersion}
        >
            {fallback}
        </div>
    ),
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
import { resolveNearYouDiscoveryPolicy } from "@/lib/data/home/discoveryRanker";

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
    mocks.getClubsByZip.mockResolvedValue([]);
    mocks.getComediansByZip.mockResolvedValue([]);
    mocks.getShowsTonight.mockResolvedValue([]);
    mocks.getShowsNearZipWithTelemetry.mockResolvedValue({
        shows: [],
        impressionContexts: {},
    });
    mocks.getTrendingShowsThisWeek.mockResolvedValue([]);
    mocks.getHeroContext.mockResolvedValue({
        city: null,
        state: null,
        zipCode: null,
    });
    mocks.getFavoriteComedianShows.mockResolvedValue([]);
    mocks.getDiscoveryRailPolicy.mockResolvedValue({
        platform: "web",
        catalogVersion: 3,
        version: 7,
        cycleCadenceHours: 24,
        rails: [],
    });
    mocks.getTouringScarcityRails.mockResolvedValue(null);
    mocks.getFreshAndRisingRails.mockResolvedValue(null);
    mocks.getAffinityRails.mockResolvedValue(null);
});

afterEach(() => {
    delete process.env.NEAR_YOU_DISCOVERY_RANKER_ENABLED;
});

function findCandidateProfileId(): string {
    for (let index = 0; index < 10_000; index += 1) {
        const profileId = `profile-${index}`;
        if (
            resolveNearYouDiscoveryPolicy({
                enabled: true,
                actorKey: `profile:${profileId}`,
            }).experimentVariant === "candidate"
        ) {
            return profileId;
        }
    }
    throw new Error("Unable to find candidate profile ID");
}

describe("HomePage favorite comedian rail", () => {
    it("selects the shared discovery policy for the web platform", async () => {
        const markup = await renderHomePage();

        expect(mocks.getDiscoveryRailPolicy).toHaveBeenCalledWith("web");
        expect(markup).toContain('data-platform="web"');
        expect(markup).toContain('data-policy-version="7"');
    });

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
        expect(mocks.getShowsNearZipWithTelemetry).toHaveBeenCalledWith(
            "10801",
            25,
            expect.objectContaining({ experimentVariant: "control" }),
        );
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
        mocks.getShowsNearZipWithTelemetry.mockResolvedValue({
            shows: Array.from({ length: 8 }, (_, index) => makeShow(index + 1)),
            impressionContexts: {},
        });

        const markup = await renderHomePage();

        expect(markup).toContain("Nearby shows");
        expect(markup).toContain('data-count="8"');
        expect(markup).toContain(
            'data-href="/show/search?zip=10801&amp;distance=25"',
        );
        expect(markup).not.toContain("More Near You");
    });

    it("uses the candidate ranker and matching presentation metadata for an assigned profile", async () => {
        process.env.NEAR_YOU_DISCOVERY_RANKER_ENABLED = "1";
        const profileId = findCandidateProfileId();
        mocks.auth.mockResolvedValue({
            profile: { id: profileId, zipCode: "10801" },
        });
        mocks.getHeroContext.mockResolvedValue({
            city: "New Rochelle",
            state: "NY",
            zipCode: "10801",
        });
        mocks.getShowsNearZipWithTelemetry.mockResolvedValue({
            shows: [makeShow(1)],
            impressionContexts: {},
        });

        const markup = await renderHomePage();

        expect(mocks.getShowsNearZipWithTelemetry).toHaveBeenCalledWith(
            "10801",
            25,
            {
                actorKey: `profile:${profileId}`,
                profileId,
                experimentVariant: "candidate",
            },
        );
        expect(markup).toContain('data-policy-version="near-you-candidate-v1"');
        expect(markup).toContain('data-experiment-variant="candidate"');
    });

    it("keeps cookieless visitors on control until a durable visitor cookie exists", async () => {
        process.env.NEAR_YOU_DISCOVERY_RANKER_ENABLED = "1";
        mocks.auth.mockResolvedValue(null);
        mocks.getHeroContext.mockResolvedValue({
            city: "New Rochelle",
            state: "NY",
            zipCode: "10801",
        });
        mocks.getShowsNearZipWithTelemetry.mockResolvedValue({
            shows: [makeShow(1)],
            impressionContexts: {},
        });

        const markup = await renderHomePage();

        expect(mocks.getShowsNearZipWithTelemetry).toHaveBeenCalledWith(
            "10801",
            25,
            {
                actorKey: null,
                profileId: undefined,
                experimentVariant: "control",
            },
        );
        expect(markup).toContain('data-policy-version="near-you-control-v1"');
        expect(markup).toContain('data-experiment-variant="control"');
    });

    it("treats an invalid oversized visitor cookie as cookieless bootstrap traffic", async () => {
        process.env.NEAR_YOU_DISCOVERY_RANKER_ENABLED = "1";
        mocks.auth.mockResolvedValue(null);
        mocks.cookies.mockResolvedValue({
            get: vi.fn((name: string) =>
                name === "lt_anon_visitor_id"
                    ? { value: "x".repeat(129) }
                    : undefined,
            ),
        });
        mocks.getHeroContext.mockResolvedValue({
            city: "New Rochelle",
            state: "NY",
            zipCode: "10801",
        });
        mocks.getShowsNearZipWithTelemetry.mockResolvedValue({
            shows: [makeShow(1)],
            impressionContexts: {},
        });

        const markup = await renderHomePage();

        expect(mocks.getShowsNearZipWithTelemetry).toHaveBeenCalledWith(
            "10801",
            25,
            expect.objectContaining({
                actorKey: null,
                experimentVariant: "control",
            }),
        );
        expect(markup).toContain('data-experiment-variant="control"');
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
