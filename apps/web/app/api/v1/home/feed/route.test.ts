import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));
vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/rateLimit", () => ({
    applyPublicReadRateLimit: vi.fn(() =>
        Promise.resolve({
            allowed: true,
            limit: 60,
            remaining: 59,
            resetAt: 0,
        }),
    ),
    rateLimitHeaders: vi.fn(),
}));
vi.mock("@/lib/data/home/getHeroContext", () => ({
    getHeroContext: vi.fn(),
}));
vi.mock("@/lib/data/home/getTrendingComedians", () => ({
    getTrendingComedians: vi.fn(),
}));
vi.mock("@/lib/data/home/getClubs", () => ({
    getClubs: vi.fn(),
}));
vi.mock("@/lib/data/home/getClubsByZip", () => ({
    getClubsByZip: vi.fn(),
}));
vi.mock("@/lib/data/home/getComediansByZip", () => ({
    getComediansByZip: vi.fn(),
}));
vi.mock("@/lib/data/home/getShowsTonight", () => ({
    getShowsTonight: vi.fn(),
}));
vi.mock("@/lib/data/home/getShowsNearZip", () => ({
    getShowsNearZip: vi.fn(),
}));
vi.mock("@/lib/data/home/getTrendingShowsThisWeek", () => ({
    getTrendingShowsThisWeek: vi.fn(),
}));
vi.mock("@/lib/data/home/getTrendingPodcasts", () => ({
    getTrendingPodcasts: vi.fn(),
}));
vi.mock("@/lib/data/home/getPodcastEpisodeDiscovery", () => ({
    getPodcastEpisodeDiscovery: vi.fn(),
}));
vi.mock("@/lib/data/home/getFavoriteComedianShows", () => ({
    getFavoriteComedianShows: vi.fn(),
}));
vi.mock("@/lib/data/home/getDiscoveryRailPolicy", () => ({
    getDiscoveryRailPolicy: vi.fn(),
}));
vi.mock("@/lib/data/home/getTouringScarcityRails", () => ({
    getTouringScarcityRails: vi.fn(),
}));
vi.mock("@/lib/data/home/getFreshAndRisingRails", () => ({
    getFreshAndRisingRails: vi.fn(),
}));
vi.mock("@/lib/data/home/getAffinityRails", () => ({
    getAffinityRails: vi.fn(),
}));

import { GET } from "./route";
import { auth } from "@/auth";
import { PROFILE_MISSING, resolveAuth } from "@/lib/auth/resolveAuth";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { getHeroContext } from "@/lib/data/home/getHeroContext";
import { getTrendingComedians } from "@/lib/data/home/getTrendingComedians";
import { getClubs } from "@/lib/data/home/getClubs";
import { getClubsByZip } from "@/lib/data/home/getClubsByZip";
import { getComediansByZip } from "@/lib/data/home/getComediansByZip";
import { getShowsTonight } from "@/lib/data/home/getShowsTonight";
import { getShowsNearZip } from "@/lib/data/home/getShowsNearZip";
import { getTrendingShowsThisWeek } from "@/lib/data/home/getTrendingShowsThisWeek";
import { getTrendingPodcasts } from "@/lib/data/home/getTrendingPodcasts";
import { getPodcastEpisodeDiscovery } from "@/lib/data/home/getPodcastEpisodeDiscovery";
import { getFavoriteComedianShows } from "@/lib/data/home/getFavoriteComedianShows";
import { getDiscoveryRailPolicy } from "@/lib/data/home/getDiscoveryRailPolicy";
import { getTouringScarcityRails } from "@/lib/data/home/getTouringScarcityRails";
import { getFreshAndRisingRails } from "@/lib/data/home/getFreshAndRisingRails";
import { getAffinityRails } from "@/lib/data/home/getAffinityRails";
import {
    getDefaultDiscoveryRailPolicy,
    type DiscoveryPlatform,
} from "@/lib/discovery/railPolicy";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";

const mockAuth = vi.mocked(auth);
const mockResolveAuth = vi.mocked(resolveAuth);
const mockApplyPublicReadRateLimit = vi.mocked(applyPublicReadRateLimit);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);
const mockGetHeroContext = vi.mocked(getHeroContext);
const mockGetTrendingComedians = vi.mocked(getTrendingComedians);
const mockGetClubs = vi.mocked(getClubs);
const mockGetClubsByZip = vi.mocked(getClubsByZip);
const mockGetComediansByZip = vi.mocked(getComediansByZip);
const mockGetShowsTonight = vi.mocked(getShowsTonight);
const mockGetShowsNearZip = vi.mocked(getShowsNearZip);
const mockGetTrendingShowsThisWeek = vi.mocked(getTrendingShowsThisWeek);
const mockGetTrendingPodcasts = vi.mocked(getTrendingPodcasts);
const mockGetPodcastEpisodeDiscovery = vi.mocked(getPodcastEpisodeDiscovery);
const mockGetFavoriteComedianShows = vi.mocked(getFavoriteComedianShows);
const mockGetDiscoveryRailPolicy = vi.mocked(getDiscoveryRailPolicy);
const mockGetTouringScarcityRails = vi.mocked(getTouringScarcityRails);
const mockGetFreshAndRisingRails = vi.mocked(getFreshAndRisingRails);
const mockGetAffinityRails = vi.mocked(getAffinityRails);

function makeRequest(
    params: Record<string, string> = {},
    headers: Record<string, string> = {},
): NextRequest {
    const url = new URL("http://localhost/api/v1/home/feed");
    for (const [k, v] of Object.entries(params)) {
        url.searchParams.set(k, v);
    }
    return new NextRequest(url.toString(), { headers });
}

function primeHappyPath() {
    mockGetTrendingComedians.mockResolvedValue([]);
    mockGetClubs.mockResolvedValue([]);
    mockGetClubsByZip.mockResolvedValue([]);
    mockGetComediansByZip.mockResolvedValue([]);
    mockGetShowsTonight.mockResolvedValue([]);
    mockGetShowsNearZip.mockResolvedValue([]);
    mockGetTrendingShowsThisWeek.mockResolvedValue([]);
    mockGetTrendingPodcasts.mockResolvedValue([]);
    mockGetPodcastEpisodeDiscovery.mockResolvedValue([]);
    mockGetFavoriteComedianShows.mockResolvedValue([]);
    mockGetTouringScarcityRails.mockResolvedValue({
        justPassingThrough: {
            railKey: "just_passing_through",
            label: "Rarely nearby",
            items: [],
        },
    });
    mockGetFreshAndRisingRails.mockResolvedValue({
        startingToBuzz: {
            railKey: "starting_to_buzz",
            label: "Shows gaining momentum",
            items: [],
        },
    });
    mockGetAffinityRails.mockResolvedValue({
        fromYourPodcasts: {
            railKey: "from_your_podcasts",
            label: "From your podcasts",
            items: [],
        },
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
    mockAuth.mockResolvedValue(null as never);
    mockResolveAuth.mockResolvedValue(null);
    mockGetHeroContext.mockResolvedValue({
        zipCode: null,
        city: null,
        state: null,
    });
    mockGetDiscoveryRailPolicy.mockImplementation(
        async (platform: DiscoveryPlatform) =>
            getDefaultDiscoveryRailPolicy(platform),
    );
    primeHappyPath();
});

describe("GET /api/v1/home/feed", () => {
    describe("rail plan", () => {
        it.each(["web", "ios", "android"] as const)(
            "returns a versioned plan for the validated %s platform",
            async (platform) => {
                mockGetShowsTonight.mockResolvedValue([{ id: 42 }] as never);

                const res = await GET(makeRequest({ platform }));
                const body = await res.json();

                expect(res.status).toBe(200);
                expect(mockGetDiscoveryRailPolicy).toHaveBeenCalledWith(
                    platform,
                );
                expect(body.data.railPlan).toMatchObject({
                    version: 1,
                    catalogVersion: 5,
                    policyVersion: 5,
                    platform,
                    rails: expect.arrayContaining([
                        {
                            railKey: "shows_tonight",
                            payloadKey: "showsTonight",
                            position: expect.any(Number),
                            itemIds: ["42"],
                        },
                    ]),
                });
            },
        );

        it("defaults older clients to web and preserves every legacy response field", async () => {
            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockGetDiscoveryRailPolicy).toHaveBeenCalledWith("web");
            expect(Object.keys(body.data)).toEqual([
                "hero",
                "trendingComedians",
                "comediansNearYou",
                "showsTonight",
                "moreNearYou",
                "trendingThisWeek",
                "followedComedianShows",
                "podcastEpisodes",
                "trendingPodcasts",
                "popularClubs",
                "dynamicRails",
                "railPlan",
            ]);
            expect(body.data.railPlan.platform).toBe("web");
        });

        it("returns 400 for an unsupported platform", async () => {
            const res = await GET(makeRequest({ platform: "desktop" }));
            const body = await res.json();

            expect(res.status).toBe(400);
            expect(body.error).toMatch(/platform/i);
            expect(mockGetHeroContext).not.toHaveBeenCalled();
            expect(mockGetDiscoveryRailPolicy).not.toHaveBeenCalled();
        });

        it("falls back to the platform default when the stored policy cannot load", async () => {
            mockGetDiscoveryRailPolicy.mockRejectedValue(
                new Error("database unavailable"),
            );

            const res = await GET(makeRequest({ platform: "ios" }));
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(body.data.railPlan).toMatchObject({
                version: 1,
                catalogVersion: 5,
                policyVersion: 5,
                platform: "ios",
            });
        });

        it("invokes every dynamic provider and preserves structured reason evidence", async () => {
            mockResolveAuth.mockResolvedValue({
                profileId: "profile-1",
                userId: "user-1",
            });
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });
            const sharedShow = { id: 71, name: "Dynamic show" };
            mockGetTouringScarcityRails.mockResolvedValue({
                justPassingThrough: {
                    railKey: "just_passing_through",
                    label: "Rarely nearby",
                    items: [
                        {
                            show: sharedShow,
                            performer: { id: 1, uuid: "comic-1", name: "Ada" },
                            reason: {
                                kind: "just_passing_through",
                                label: "Ada is visiting New York",
                                evidence: { canonicalComedianId: 1 },
                            },
                        },
                    ],
                },
            } as never);
            mockGetFreshAndRisingRails.mockResolvedValue({
                startingToBuzz: {
                    railKey: "starting_to_buzz",
                    label: "Shows gaining momentum",
                    items: [
                        {
                            show: sharedShow,
                            performer: { id: 1, uuid: "comic-1", name: "Ada" },
                            reason: {
                                kind: "starting_to_buzz",
                                label: "Demand is accelerating",
                                evidence: { momentum: 0.8, confidence: 0.9 },
                            },
                        },
                    ],
                },
            } as never);
            mockGetAffinityRails.mockResolvedValue({
                fromYourPodcasts: {
                    railKey: "from_your_podcasts",
                    label: "From your podcasts",
                    items: [],
                },
            } as never);
            mockGetDiscoveryRailPolicy.mockResolvedValue({
                platform: "web",
                catalogVersion: 5,
                version: 5,
                cycleCadenceHours: 24,
                rails: ["just_passing_through", "starting_to_buzz"].map(
                    (railKey, position) => ({
                        railKey,
                        enabled: true,
                        position,
                        rotationPool: null,
                        weight: 1,
                    }),
                ),
            } as never);

            const res = await GET(
                makeRequest({ zip: "10001", distance: "40" }),
            );
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockGetTouringScarcityRails).toHaveBeenCalledWith({
                zipCode: "10001",
                radiusMiles: 40,
            });
            expect(mockGetFreshAndRisingRails).toHaveBeenCalledWith();
            expect(mockGetAffinityRails).toHaveBeenCalledWith("profile-1");
            expect(body.data.dynamicRails).toHaveLength(2);
            expect(body.data.dynamicRails).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({
                        railKey: "just_passing_through",
                        items: [
                            expect.objectContaining({
                                id: 71,
                                show: sharedShow,
                                reason: expect.objectContaining({
                                    kind: "just_passing_through",
                                    evidence: { canonicalComedianId: 1 },
                                }),
                            }),
                        ],
                    }),
                    expect.objectContaining({
                        railKey: "starting_to_buzz",
                        items: [
                            expect.objectContaining({
                                id: 71,
                                reason: expect.objectContaining({
                                    evidence: {
                                        momentum: 0.8,
                                        confidence: 0.9,
                                    },
                                }),
                            }),
                        ],
                    }),
                ]),
            );
            expect(body.data.railPlan.rails).toEqual([
                {
                    railKey: "just_passing_through",
                    payloadKey: "dynamicRails",
                    position: 0,
                    itemIds: ["71"],
                },
            ]);
        });

        it("isolates dynamic provider failures", async () => {
            mockGetFreshAndRisingRails.mockRejectedValue(
                new Error("snapshot unavailable"),
            );

            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(body.data.dynamicRails).toEqual([]);
        });

        it("deduplicates plan shows by policy priority without changing the legacy field", async () => {
            mockResolveAuth.mockResolvedValue({
                profileId: "profile-1",
                userId: "user-1",
            });
            mockGetFavoriteComedianShows.mockResolvedValue([
                { id: 42 },
            ] as never);
            mockGetShowsTonight.mockResolvedValue([
                { id: 42 },
                { id: 43 },
            ] as never);
            mockGetDiscoveryRailPolicy.mockResolvedValue({
                platform: "web",
                catalogVersion: 5,
                version: 5,
                cycleCadenceHours: 24,
                rails: [
                    {
                        railKey: "followed_comedian_shows",
                        enabled: true,
                        position: 0,
                        rotationPool: null,
                        weight: 1,
                    },
                    {
                        railKey: "shows_tonight",
                        enabled: true,
                        position: 1,
                        rotationPool: null,
                        weight: 1,
                    },
                ],
            });

            const res = await GET(makeRequest());
            const body = await res.json();

            expect(body.data.followedComedianShows).toEqual([]);
            expect(body.data.railPlan.rails).toEqual([
                {
                    railKey: "followed_comedian_shows",
                    payloadKey: "followedComedianShows",
                    position: 0,
                    itemIds: ["42"],
                },
                {
                    railKey: "shows_tonight",
                    payloadKey: "showsTonight",
                    position: 1,
                    itemIds: ["43"],
                },
            ]);
        });
    });

    describe("zip validation", () => {
        it("returns 400 when zip is not a 5-digit code", async () => {
            const res = await GET(makeRequest({ zip: "abc" }));
            const body = await res.json();

            expect(res.status).toBe(400);
            expect(body.error).toMatch(/zip/i);
            expect(mockGetHeroContext).not.toHaveBeenCalled();
        });

        it("attaches rateLimitHeaders to the 400 response", async () => {
            const res = await GET(makeRequest({ zip: "abc" }));

            expect(res.status).toBe(400);
            expect(mockRateLimitHeaders).toHaveBeenCalled();
            expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
                RATE_LIMIT_SENTINEL_VALUE,
            );
        });

        it("accepts a valid 5-digit zip", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });

            const res = await GET(makeRequest({ zip: "10001" }));

            expect(res.status).toBe(200);
            expect(mockGetHeroContext).toHaveBeenCalledWith("10001");
        });

        it("passes ?distance= to zip-scoped recommendation fetches", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "94108",
                city: "San Francisco",
                state: "CA",
            });

            const res = await GET(
                makeRequest({ zip: "94108", distance: "50" }),
            );

            expect(res.status).toBe(200);
            expect(mockGetTrendingComedians).toHaveBeenCalledWith(8, 0, {
                zipCode: "94108",
                distanceMiles: 50,
            });
            expect(mockGetComediansByZip).toHaveBeenCalledWith("94108", 50);
            expect(mockGetShowsTonight).toHaveBeenCalledWith(
                "UTC",
                "94108",
                50,
            );
            expect(mockGetShowsNearZip).toHaveBeenCalledWith("94108", 50);
            expect(mockGetClubsByZip).toHaveBeenCalledWith("94108", 50, 8, {
                requireImage: true,
            });
            expect(mockGetTrendingShowsThisWeek).toHaveBeenCalledWith(
                "UTC",
                "94108",
                50,
            );
            expect(mockGetTrendingPodcasts).toHaveBeenCalledWith(
                "94108",
                undefined,
                50,
            );
        });

        it("returns 400 when distance is outside the supported range", async () => {
            const res = await GET(makeRequest({ zip: "94108", distance: "0" }));
            const body = await res.json();

            expect(res.status).toBe(400);
            expect(body.error).toMatch(/distance/i);
            expect(mockGetHeroContext).not.toHaveBeenCalled();
        });

        it("returns 400 quickly when distance is 500 miles", async () => {
            const res = await GET(
                makeRequest({ zip: "94108", distance: "500" }),
            );
            const body = await res.json();

            expect(res.status).toBe(400);
            expect(body.error).toBe(
                "distance must be a number between 1 and 100 miles",
            );
            expect(mockGetHeroContext).not.toHaveBeenCalled();
        });
    });

    describe("zipCode resolution precedence", () => {
        it("passes ?zip= to getHeroContext when query param is set (overrides session zip)", async () => {
            mockAuth.mockResolvedValue({
                profile: { zipCode: "90210", userid: "user-1" },
            } as never);

            await GET(makeRequest({ zip: "10001" }));

            expect(mockGetHeroContext).toHaveBeenCalledWith("10001");
        });

        it("falls back to session profile zipCode when ?zip is absent", async () => {
            mockAuth.mockResolvedValue({
                profile: { zipCode: "90210", userid: "user-1" },
            } as never);

            await GET(makeRequest());

            expect(mockGetHeroContext).toHaveBeenCalledWith("90210");
        });

        it("passes null to getHeroContext when neither ?zip nor session zip exist", async () => {
            await GET(makeRequest());

            expect(mockGetHeroContext).toHaveBeenCalledWith(null);
        });

        it("keeps trending comedians generic when no zip can be resolved", async () => {
            await GET(makeRequest());

            expect(mockGetTrendingComedians).toHaveBeenCalledWith();
        });
    });

    describe("null zipCode path", () => {
        it("skips zip-based fetches and returns empty near-you sections", async () => {
            // getHeroContext already returns { zipCode: null } from beforeEach
            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockGetComediansByZip).not.toHaveBeenCalled();
            expect(mockGetShowsNearZip).not.toHaveBeenCalled();
            expect(body.data.comediansNearYou).toEqual([]);
            expect(body.data.moreNearYou).toEqual([]);
            expect(body.data.hero.shows).toEqual([]);
        });
    });

    describe("popularClubs zip-scoping", () => {
        it("returns zip-scoped clubs and does not fall back when nearby clubs exist", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });
            mockGetClubsByZip.mockResolvedValue([
                { id: 1, name: "Local Club" },
            ] as never);

            const res = await GET(makeRequest({ zip: "10001" }));
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockGetClubsByZip).toHaveBeenCalled();
            expect(
                body.data.popularClubs.map((c: { id: number }) => c.id),
            ).toEqual([1]);
            // Nearby clubs found → no global fallback fetch.
            expect(mockGetClubs).not.toHaveBeenCalled();
        });

        it("falls back to the global club list when no nearby clubs are found", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "59718",
                city: "Bozeman",
                state: "MT",
            });
            mockGetClubsByZip.mockResolvedValue([]);
            mockGetClubs.mockResolvedValue([
                { id: 99, name: "Global Club" },
            ] as never);

            const res = await GET(makeRequest({ zip: "59718" }));
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockGetClubsByZip).toHaveBeenCalled();
            expect(mockGetClubs).toHaveBeenCalledWith(8, 0, {
                requireImage: true,
            });
            expect(
                body.data.popularClubs.map((c: { id: number }) => c.id),
            ).toEqual([99]);
        });

        it("uses the global club list (no zip-scoped fetch) when no zip resolves", async () => {
            mockGetClubs.mockResolvedValue([
                { id: 42, name: "Global Club" },
            ] as never);

            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockGetClubsByZip).not.toHaveBeenCalled();
            expect(mockGetClubs).toHaveBeenCalledWith(8, 0, {
                requireImage: true,
            });
            expect(
                body.data.popularClubs.map((c: { id: number }) => c.id),
            ).toEqual([42]);
        });
    });

    describe("hero.shows slicing", () => {
        it("puts the first 3 showsNearZip into hero.shows and the rest into moreNearYou", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });
            mockGetShowsNearZip.mockResolvedValue([
                {
                    id: 1,
                    clubId: 7,
                    imageUrl: "https://cdn.example.com/1.jpg",
                    soldOut: false,
                },
                { id: 2 },
                { id: 3 },
                { id: 4 },
                { id: 5 },
            ] as never);

            const res = await GET(makeRequest({ zip: "10001" }));
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(
                body.data.hero.shows.map((s: { id: number }) => s.id),
            ).toEqual([1, 2, 3]);
            expect(
                body.data.moreNearYou.map((s: { id: number }) => s.id),
            ).toEqual([4, 5]);
            // Pin representative camelCase show keys on hero.shows so a
            // future regression (e.g. clubId → club_id) surfaces here.
            expect(body.data.hero.shows[0].clubId).toBe(7);
            expect(body.data.hero.shows[0].imageUrl).toBe(
                "https://cdn.example.com/1.jpg",
            );
            expect(body.data.hero.shows[0].soldOut).toBe(false);
        });

        it("returns empty moreNearYou when fewer than 3 near-you shows exist", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });
            mockGetShowsNearZip.mockResolvedValue([
                { id: 1 },
                { id: 2 },
            ] as never);

            const res = await GET(makeRequest({ zip: "10001" }));
            const body = await res.json();

            expect(
                body.data.hero.shows.map((s: { id: number }) => s.id),
            ).toEqual([1, 2]);
            expect(body.data.moreNearYou).toEqual([]);
        });
    });

    describe("followedComedianShows", () => {
        it("returns followed-comedian shows for a native bearer-authenticated profile", async () => {
            mockResolveAuth.mockResolvedValue({
                profileId: "profile-1",
                userId: "user-1",
            });
            mockGetFavoriteComedianShows.mockResolvedValue([
                { id: 41, name: "Favorite Comic Night" },
            ] as never);

            const res = await GET(
                makeRequest({}, { Authorization: "Bearer native-token" }),
            );
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockResolveAuth).toHaveBeenCalledWith(
                expect.any(NextRequest),
            );
            expect(mockGetFavoriteComedianShows).toHaveBeenCalledWith(
                "profile-1",
            );
            expect(body.data.followedComedianShows).toEqual([
                { id: 41, name: "Favorite Comic Night" },
            ]);
        });

        it("deduplicates shows already present in higher-priority show sections", async () => {
            mockResolveAuth.mockResolvedValue({
                profileId: "profile-1",
                userId: "user-1",
            });
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });
            mockGetShowsNearZip.mockResolvedValue([
                { id: 1 },
                { id: 2 },
            ] as never);
            mockGetShowsTonight.mockResolvedValue([{ id: 3 }] as never);
            mockGetTrendingShowsThisWeek.mockResolvedValue([
                { id: 4 },
            ] as never);
            mockGetFavoriteComedianShows.mockResolvedValue([
                { id: 1 },
                { id: 2 },
                { id: 3 },
                { id: 4 },
                { id: 9 },
            ] as never);

            const res = await GET(makeRequest());
            const body = await res.json();

            expect(body.data.followedComedianShows).toEqual([{ id: 9 }]);
        });

        it("returns an empty section for signed-out users without querying favorites", async () => {
            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockGetFavoriteComedianShows).not.toHaveBeenCalled();
            expect(body.data.followedComedianShows).toEqual([]);
        });

        it("returns an empty section when the authenticated profile has no matching shows", async () => {
            mockResolveAuth.mockResolvedValue({
                profileId: "profile-1",
                userId: "user-1",
            });

            const res = await GET(makeRequest());
            const body = await res.json();

            expect(mockGetFavoriteComedianShows).toHaveBeenCalledWith(
                "profile-1",
            );
            expect(body.data.followedComedianShows).toEqual([]);
        });

        it("treats an authenticated user without a profile as signed out", async () => {
            mockResolveAuth.mockResolvedValue(PROFILE_MISSING);

            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockGetFavoriteComedianShows).not.toHaveBeenCalled();
            expect(body.data.followedComedianShows).toEqual([]);
        });

        it("isolates followed-comedian query failures to an empty section", async () => {
            mockResolveAuth.mockResolvedValue({
                profileId: "profile-1",
                userId: "user-1",
            });
            mockGetFavoriteComedianShows.mockRejectedValue(new Error("boom"));

            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(body.data.followedComedianShows).toEqual([]);
        });
    });

    describe("trendingPodcasts", () => {
        it("returns a shape-correct trendingPodcasts array", async () => {
            mockGetTrendingPodcasts.mockResolvedValue([
                {
                    id: 42,
                    slug: "good-one",
                    title: "Good One",
                    authorName: "Vulture",
                    websiteUrl: "https://example.com/good-one",
                    feedUrl: "https://example.com/feed.xml",
                    imageUrl: "https://cdn.example.com/good-one.jpg",
                    description: "Comedy interviews",
                    episodeCount: 12,
                    hosts: [],
                },
            ]);

            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(body.data.trendingPodcasts).toEqual([
                {
                    id: 42,
                    slug: "good-one",
                    title: "Good One",
                    authorName: "Vulture",
                    websiteUrl: "https://example.com/good-one",
                    feedUrl: "https://example.com/feed.xml",
                    imageUrl: "https://cdn.example.com/good-one.jpg",
                    description: "Comedy interviews",
                    episodeCount: 12,
                    hosts: [],
                },
            ]);
            expect(mockGetTrendingPodcasts).toHaveBeenCalledWith(
                null,
                undefined,
                25,
            );
        });
    });

    describe("podcast episode discovery", () => {
        const recommendation = {
            id: 101,
            title: "A Fresh Episode",
            description: null,
            releaseDate: "2026-08-06T12:00:00.000Z",
            durationSeconds: 3600,
            episodeUrl: "https://example.com/episodes/101",
            audioUrl: "https://cdn.example.com/episodes/101.mp3",
            podcast: {
                id: 42,
                slug: "good-one",
                title: "Good One",
                imageUrl: "https://cdn.example.com/good-one.jpg",
            },
            recommendation: {
                reason: "followed_comedian",
                comedian: {
                    id: 7,
                    uuid: "comedian-7",
                    name: "Example Comic",
                    imageUrl: "https://cdn.example.com/comic.jpg",
                },
                appearanceRole: "guest",
                followedComedian: true,
                favoritePodcast: false,
            },
        };

        it("returns personalized episodes and retains trending podcasts for authenticated callers", async () => {
            mockResolveAuth.mockResolvedValue({
                profileId: "profile-1",
                userId: "user-1",
            });
            mockGetPodcastEpisodeDiscovery.mockResolvedValue([
                recommendation,
            ] as never);
            mockGetTrendingPodcasts.mockResolvedValue([
                { id: 42, title: "Good One" },
            ] as never);

            const res = await GET(
                makeRequest({}, { Authorization: "Bearer native-token" }),
            );
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockGetPodcastEpisodeDiscovery).toHaveBeenCalledWith(
                "profile-1",
            );
            expect(body.data.podcastEpisodes).toEqual([recommendation]);
            expect(body.data.trendingPodcasts).toEqual([
                { id: 42, title: "Good One" },
            ]);
        });

        it("returns anonymous episode discovery and retains trending podcasts", async () => {
            mockGetPodcastEpisodeDiscovery.mockResolvedValue([
                recommendation,
            ] as never);
            mockGetTrendingPodcasts.mockResolvedValue([
                { id: 42, title: "Good One" },
            ] as never);

            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockGetPodcastEpisodeDiscovery).toHaveBeenCalledWith(null);
            expect(body.data.podcastEpisodes).toEqual([recommendation]);
            expect(body.data.trendingPodcasts).toEqual([
                { id: 42, title: "Good One" },
            ]);
        });

        it("isolates discovery failures to an empty episode section", async () => {
            mockGetPodcastEpisodeDiscovery.mockRejectedValue(new Error("boom"));

            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(body.data.podcastEpisodes).toEqual([]);
            expect(body.data.trendingPodcasts).toEqual([]);
        });
    });

    describe("getHeroContext rejection", () => {
        it("falls back to a null hero and still returns 200", async () => {
            mockGetHeroContext.mockRejectedValueOnce(new Error("hero boom"));

            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(body.data.hero).toEqual({
                zipCode: null,
                city: null,
                state: null,
                shows: [],
            });
            expect(body.data.comediansNearYou).toEqual([]);
            expect(body.data.moreNearYou).toEqual([]);
        });
    });

    describe("per-section failure isolation", () => {
        it("returns 200 with empty arrays for sections whose helper rejects", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });
            mockGetComediansByZip.mockRejectedValue(new Error("boom"));
            mockGetShowsNearZip.mockRejectedValue(new Error("boom"));
            mockGetTrendingComedians.mockRejectedValue(new Error("boom"));

            const res = await GET(makeRequest({ zip: "10001" }));
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(body.data.comediansNearYou).toEqual([]);
            expect(body.data.moreNearYou).toEqual([]);
            expect(body.data.trendingComedians).toEqual([]);
        });
    });

    describe("cache headers", () => {
        it("emits Cache-Control: private on the 200 response", async () => {
            const res = await GET(makeRequest());

            expect(res.status).toBe(200);
            expect(res.headers.get("Cache-Control")).toContain("private");
        });
    });

    describe("X-Timezone forwarding", () => {
        it("forwards the X-Timezone header to getShowsTonight and getTrendingShowsThisWeek", async () => {
            await GET(makeRequest({}, { "X-Timezone": "America/Los_Angeles" }));

            expect(mockGetShowsTonight).toHaveBeenCalledWith(
                "America/Los_Angeles",
            );
            expect(mockGetTrendingShowsThisWeek).toHaveBeenCalledWith(
                "America/Los_Angeles",
            );
        });

        it("passes the resolved ZIP to getShowsTonight so the titled section is local", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10801",
                city: "New Rochelle",
                state: "NY",
            });

            await GET(makeRequest({ zip: "10801" }));

            expect(mockGetShowsTonight).toHaveBeenCalledWith(
                "UTC",
                "10801",
                expect.any(Number),
            );
        });

        it("passes the resolved ZIP to getTrendingShowsThisWeek so the iOS rail is local", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });

            await GET(makeRequest({ zip: "10001" }));

            expect(mockGetTrendingShowsThisWeek).toHaveBeenCalledWith(
                "UTC",
                "10001",
                expect.any(Number),
            );
        });

        it("defaults to UTC when X-Timezone is absent", async () => {
            await GET(makeRequest());

            expect(mockGetShowsTonight).toHaveBeenCalledWith("UTC");
            expect(mockGetTrendingShowsThisWeek).toHaveBeenCalledWith("UTC");
        });

        it("returns 400 when X-Timezone is not a valid IANA zone", async () => {
            const res = await GET(
                makeRequest({}, { "X-Timezone": "Not/Real" }),
            );
            const body = await res.json();

            expect(res.status).toBe(400);
            expect(body.error).toMatch(/X-Timezone/);
            expect(mockGetShowsTonight).not.toHaveBeenCalled();
            expect(mockGetTrendingShowsThisWeek).not.toHaveBeenCalled();
        });
    });

    describe("rate limiting", () => {
        it("returns the helper's NextResponse when the rate limit is exceeded", async () => {
            const fakeResponse = NextResponse.json(
                { error: "Too Many Requests" },
                { status: 429 },
            );
            mockApplyPublicReadRateLimit.mockResolvedValueOnce(fakeResponse);

            const res = await GET(makeRequest());

            expect(res).toBe(fakeResponse);
            expect(mockGetHeroContext).not.toHaveBeenCalled();
        });

        it('invokes applyPublicReadRateLimit with the "home" route prefix', async () => {
            await GET(makeRequest());

            expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
                expect.any(NextRequest),
                "home",
            );
        });
    });

    describe("unexpected failures", () => {
        it("returns 500 with rate-limit headers when auth fails unexpectedly", async () => {
            mockAuth.mockRejectedValue(new Error("auth unavailable"));

            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(500);
            expect(body).toEqual({ error: "Failed to fetch home feed" });
            expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
                RATE_LIMIT_SENTINEL_VALUE,
            );
        });
    });
});
