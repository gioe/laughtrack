import { DISCOVERY_RAIL_CATALOG_VERSION } from "@/lib/discovery/railPolicy";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
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
            label: "Here for a Limited Time",
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
                mockGetShowsTonight.mockResolvedValue(
                    [{ id: 42 }].map((show) => ({
                        ...show,
                        date: new Date(Date.UTC(2026, 8, 15, 18, show.id)),
                    })) as never,
                );

                const res = await GET(makeRequest({ platform }));
                const body = await res.json();

                expect(res.status).toBe(200);
                expect(mockGetDiscoveryRailPolicy).toHaveBeenCalledWith(
                    platform,
                );
                expect(body.data.railPlan).toMatchObject({
                    version: 1,
                    catalogVersion: DISCOVERY_RAIL_CATALOG_VERSION,
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
                catalogVersion: DISCOVERY_RAIL_CATALOG_VERSION,
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
                    label: "Here for a Limited Time",
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
                catalogVersion: DISCOVERY_RAIL_CATALOG_VERSION,
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
                limit: 50,
                forFeedCandidates: true,
            });
            expect(mockGetFreshAndRisingRails).toHaveBeenCalledWith({
                limit: 50,
            });
            expect(mockGetAffinityRails).not.toHaveBeenCalled();
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
                {
                    railKey: "starting_to_buzz",
                    payloadKey: "dynamicRails",
                    position: 1,
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

        it("preserves a sparse personalized rail and keeps its planned IDs resolvable", async () => {
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
                catalogVersion: DISCOVERY_RAIL_CATALOG_VERSION,
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

            expect(body.data.followedComedianShows).toEqual([{ id: 42 }]);
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
                    itemIds: ["42", "43"],
                },
            ]);
        });
    });

    describe("feed candidate diversity", () => {
        it("selects alternatives beyond eight, resolves canonical performers, and retains dynamic evidence", async () => {
            const comedian = (id: number) => ({
                id,
                uuid: `comic-${id}`,
                name: `Comic ${id}`,
                imageUrl: "",
            });
            const show = (id: number, performerId: number) => ({
                id,
                clubId: 1,
                name: `Show ${id}`,
                imageUrl: "",
                date: new Date(Date.UTC(2026, 8, 15, 18, id)),
                lineup: [comedian(performerId)],
            });
            const tonight = Array.from({ length: 8 }, (_, i) =>
                show(i + 1, i + 1),
            );
            // The first card is an alias of canonical comedian 1.
            tonight[0].lineup = [
                { ...comedian(101), parentComedian: comedian(1) },
            ] as never;
            const week = Array.from({ length: 16 }, (_, i) =>
                show(101 + i, i + 1),
            );
            const visitors = [1, 9, 17, 18, 19, 20, 21, 22, 23, 24].map(
                (id, i) => ({
                    show: show(201 + i, 999),
                    performer: comedian(id),
                    reason: {
                        kind: "just_passing_through",
                        label: `Visitor ${id}`,
                        evidence: {
                            canonicalComedianId: id,
                            localDateCount: 2,
                        },
                    },
                }),
            );
            mockGetShowsTonight.mockResolvedValue(tonight);
            mockGetTrendingShowsThisWeek.mockResolvedValue(week);
            mockGetTouringScarcityRails.mockResolvedValue({
                justPassingThrough: {
                    railKey: "just_passing_through",
                    label: "Here for a Limited Time",
                    items: visitors,
                },
            } as never);
            mockGetDiscoveryRailPolicy.mockResolvedValue({
                platform: "ios",
                catalogVersion: DISCOVERY_RAIL_CATALOG_VERSION,
                version: 5,
                cycleCadenceHours: 24,
                rails: [
                    "shows_tonight",
                    "trending_this_week",
                    "just_passing_through",
                ].map((railKey, position) => ({
                    railKey,
                    position,
                    enabled: true,
                    rotationPool: null,
                    weight: 1,
                })),
            } as never);

            const response = await GET(makeRequest({ platform: "ios" }));
            const { data } = await response.json();
            expect(response.status).toBe(200);
            expect(
                data.showsTonight.map((item: { id: number }) => item.id),
            ).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
            expect(
                data.trendingThisWeek.map((item: { id: number }) => item.id),
            ).toEqual([109, 110, 111, 112, 113, 114, 115, 116]);
            const scarcity = data.dynamicRails[0];
            expect(
                scarcity.items.map((item: { id: number }) => item.id),
            ).toEqual([203, 204, 205, 206, 207, 208, 209, 210]);
            expect(
                scarcity.items.map((item: { reason: unknown }) => item.reason),
            ).toEqual(visitors.slice(2).map((item) => item.reason));
            for (const rail of data.railPlan.rails) {
                const payload =
                    rail.payloadKey === "dynamicRails"
                        ? data.dynamicRails.find(
                              (item: { railKey: string }) =>
                                  item.railKey === rail.railKey,
                          ).items
                        : data[rail.payloadKey];
                expect(payload).toHaveLength(8);
                expect(rail.itemIds).toEqual(
                    payload.map((item: { id: number }) => String(item.id)),
                );
            }
            // Candidate source arrays and wrapped evidence remain unchanged.
            expect(week).toHaveLength(16);
            expect(visitors).toHaveLength(10);
        });
    });

    describe("optional provider deadlines", () => {
        beforeEach(() => {
            vi.useFakeTimers();
            vi.setSystemTime(new Date("2026-09-22T15:00:00Z"));
        });
        afterEach(() => vi.useRealTimers());

        function deferred<T>() {
            let resolve!: (value: T) => void;
            let reject!: (error: Error) => void;
            const promise = new Promise<T>((yes, no) => {
                resolve = yes;
                reject = no;
            });
            return { promise, resolve, reject };
        }

        function assertResolvable(data: any) {
            for (const rail of data.railPlan.rails) {
                const items =
                    rail.payloadKey === "dynamicRails"
                        ? data.dynamicRails.find(
                              (value: any) => value.railKey === rail.railKey,
                          )?.items
                        : data[rail.payloadKey];
                for (const id of rail.itemIds) {
                    expect(
                        items.some((item: any) => String(item.id) === id),
                    ).toBe(true);
                }
            }
        }

        it.each([null, "profile-budget"])(
            "returns primary content at one 750 ms deadline with slow podcasts for %s",
            async (profileId) => {
                if (profileId)
                    mockResolveAuth.mockResolvedValue({
                        profileId,
                        userId: "user-budget",
                    });
                const episodes = deferred<never[]>();
                const podcasts = deferred<never[]>();
                mockGetPodcastEpisodeDiscovery.mockReturnValue(
                    episodes.promise,
                );
                mockGetTrendingPodcasts.mockReturnValue(podcasts.promise);
                mockGetShowsTonight.mockResolvedValue([{ id: 42 }] as never);
                let completed = false;
                const request = GET(makeRequest({ platform: "ios" })).then(
                    (response) => {
                        completed = true;
                        return response;
                    },
                );
                await vi.advanceTimersByTimeAsync(749);
                expect(completed).toBe(false);
                await vi.advanceTimersByTimeAsync(1);
                const response = await request;
                const { data } = await response.json();
                expect(response.status).toBe(200);
                expect(data.showsTonight).toEqual([{ id: 42 }]);
                expect(data.podcastEpisodes).toEqual([]);
                expect(data.trendingPodcasts).toEqual([]);
                expect(response.headers.get("Cache-Control")).toBe(
                    "private, no-store",
                );
                expect(mockGetPodcastEpisodeDiscovery).toHaveBeenCalledWith(
                    profileId,
                );
                assertResolvable(data);
                episodes.resolve([]);
                podcasts.resolve([]);
                await vi.advanceTimersByTimeAsync(0);
            },
        );

        it("returns a coherent empty plan at the deadline when local inventory is empty and podcasts stall", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });
            const episodes = deferred<never[]>();
            mockGetPodcastEpisodeDiscovery.mockReturnValueOnce(
                episodes.promise,
            );
            let completed = false;
            const request = GET(
                makeRequest({ platform: "ios", zip: "10001" }),
            ).then((response) => {
                completed = true;
                return response;
            });
            await vi.advanceTimersByTimeAsync(749);
            expect(completed).toBe(false);
            await vi.advanceTimersByTimeAsync(1);
            const response = await request;
            const { data } = await response.json();
            expect(response.status).toBe(200);
            expect(data.hero).toEqual({
                zipCode: "10001",
                city: "New York",
                state: "NY",
                shows: [],
            });
            expect(data.showsTonight).toEqual([]);
            expect(data.trendingThisWeek).toEqual([]);
            expect(data.moreNearYou).toEqual([]);
            expect(data.podcastEpisodes).toEqual([]);
            expect(data.railPlan.rails).toEqual([]);
            expect(response.headers.get("Cache-Control")).toBe(
                "private, no-store",
            );
            episodes.resolve([]);
            await vi.advanceTimersByTimeAsync(0);
        });

        it("does not start a global club fallback after the local query outlives its deadline", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });
            const clubs = deferred<never[]>();
            mockGetClubsByZip.mockReturnValueOnce(clubs.promise);
            const request = GET(makeRequest({ platform: "ios", zip: "10001" }));
            await vi.advanceTimersByTimeAsync(750);
            const response = await request;
            expect(response.status).toBe(200);
            expect((await response.json()).data.popularClubs).toEqual([]);
            expect(mockGetClubsByZip).toHaveBeenCalledOnce();
            expect(mockGetClubs).not.toHaveBeenCalled();
            clubs.resolve([]);
            await vi.advanceTimersByTimeAsync(0);
            expect(mockGetClubs).not.toHaveBeenCalled();
        });

        it("waits for slow primary content after the optional deadline", async () => {
            const primary = deferred<never[]>();
            mockGetShowsTonight.mockReturnValue(primary.promise);
            let completed = false;
            const request = GET(makeRequest()).then((response) => {
                completed = true;
                return response;
            });
            await vi.advanceTimersByTimeAsync(1000);
            expect(completed).toBe(false);
            primary.resolve([{ id: 51 }] as never);
            const { data } = await (await request).json();
            expect(data.showsTonight).toEqual([{ id: 51 }]);
            assertResolvable(data);
        });

        it.each([false, true])(
            "keeps ready optional content when local primary inventory fails=%s",
            async (fails) => {
                mockGetHeroContext.mockResolvedValue({
                    zipCode: "10001",
                    city: "New York",
                    state: "NY",
                });
                if (fails) {
                    mockGetShowsTonight.mockRejectedValue(
                        new Error("primary unavailable"),
                    );
                    mockGetShowsNearZip.mockRejectedValue(
                        new Error("nearby unavailable"),
                    );
                    mockGetTrendingShowsThisWeek.mockRejectedValue(
                        new Error("week unavailable"),
                    );
                    mockGetTrendingComedians.mockRejectedValue(
                        new Error("comedians unavailable"),
                    );
                }
                mockGetPodcastEpisodeDiscovery.mockResolvedValue([
                    { id: 61 },
                ] as never);
                const response = await GET(makeRequest({ platform: "ios" }));
                const { data } = await response.json();
                expect(response.status).toBe(200);
                expect(data.hero.shows).toEqual([]);
                expect(data.showsTonight).toEqual([]);
                expect(data.podcastEpisodes).toEqual([{ id: 61 }]);
                expect(data.railPlan.rails).toContainEqual(
                    expect.objectContaining({
                        railKey: "trending_podcasts",
                        itemIds: ["61"],
                    }),
                );
                assertResolvable(data);
            },
        );

        it.each(["resolve", "reject"] as const)(
            "ignores late %s and retries completed personalized work on refresh",
            async (settlement) => {
                mockResolveAuth.mockResolvedValue({
                    profileId: "profile-late",
                    userId: "user-late",
                });
                const late = deferred<never[]>();
                mockGetPodcastEpisodeDiscovery.mockReturnValueOnce(
                    late.promise,
                );
                const request = GET(makeRequest({ platform: "ios" }));
                await vi.advanceTimersByTimeAsync(750);
                const response = await request;
                const serialized = await response.text();
                if (settlement === "resolve")
                    late.resolve([{ id: 71 }] as never);
                else late.reject(new Error("late database failure"));
                await vi.advanceTimersByTimeAsync(0);
                expect(JSON.parse(serialized).data.podcastEpisodes).toEqual([]);
                mockGetPodcastEpisodeDiscovery.mockResolvedValue([
                    { id: 72 },
                ] as never);
                const { data } = await (
                    await GET(makeRequest({ platform: "ios" }))
                ).json();
                expect(data.podcastEpisodes).toEqual([{ id: 72 }]);
                expect(mockGetPodcastEpisodeDiscovery).toHaveBeenCalledTimes(2);
                expect(mockGetPodcastEpisodeDiscovery.mock.calls).toEqual([
                    ["profile-late"],
                    ["profile-late"],
                ]);
                assertResolvable(data);
            },
        );

        it("coalesces timed-out work only for the same profile and releases it after settlement", async () => {
            const pending = deferred<never[]>();
            mockGetPodcastEpisodeDiscovery.mockImplementation((profileId) =>
                profileId === "profile-a"
                    ? pending.promise
                    : Promise.resolve([{ id: 82 }] as never),
            );
            mockResolveAuth.mockResolvedValue({
                profileId: "profile-a",
                userId: "user-a",
            });
            const first = GET(makeRequest({ platform: "ios" }));
            await vi.advanceTimersByTimeAsync(750);
            expect((await (await first).json()).data.podcastEpisodes).toEqual(
                [],
            );
            const repeated = GET(makeRequest({ platform: "ios" }));
            await vi.advanceTimersByTimeAsync(0);
            mockResolveAuth.mockResolvedValue({
                profileId: "profile-b",
                userId: "user-b",
            });
            const isolated = await GET(makeRequest({ platform: "ios" }));
            expect((await isolated.json()).data.podcastEpisodes).toEqual([
                { id: 82 },
            ]);
            expect(mockGetPodcastEpisodeDiscovery.mock.calls).toEqual([
                ["profile-a"],
                ["profile-b"],
            ]);
            pending.resolve([{ id: 81 }] as never);
            await vi.advanceTimersByTimeAsync(0);
            expect(
                (await (await repeated).json()).data.podcastEpisodes,
            ).toEqual([{ id: 81 }]);
        });

        it("falls back after 150 ms when policy loading stalls", async () => {
            const pending =
                deferred<ReturnType<typeof getDefaultDiscoveryRailPolicy>>();
            mockGetDiscoveryRailPolicy.mockReturnValueOnce(pending.promise);
            mockGetShowsTonight.mockResolvedValue([{ id: 91 }] as never);
            let completed = false;
            const request = GET(makeRequest({ platform: "ios" })).then(
                (response) => {
                    completed = true;
                    return response;
                },
            );
            await vi.advanceTimersByTimeAsync(149);
            expect(completed).toBe(false);
            await vi.advanceTimersByTimeAsync(1);
            const { data } = await (await request).json();
            expect(data.railPlan.policyVersion).toBe(
                getDefaultDiscoveryRailPolicy("ios").version,
            );
            expect(data.showsTonight).toEqual([{ id: 91 }]);
            assertResolvable(data);
            pending.resolve(getDefaultDiscoveryRailPolicy("ios"));
            await vi.advanceTimersByTimeAsync(0);
        });

        it("skips disabled dynamic providers but retains disabled static payloads for legacy iOS category tabs", async () => {
            const policy = getDefaultDiscoveryRailPolicy("ios");
            policy.rails = policy.rails.map((rail) => ({
                ...rail,
                enabled: ![
                    "popular_clubs",
                    "just_passing_through",
                    "starting_to_buzz",
                ].includes(rail.railKey),
            }));
            mockGetDiscoveryRailPolicy.mockResolvedValue(policy);
            mockGetClubs.mockResolvedValue([{ id: 101 }] as never);
            const { data } = await (
                await GET(makeRequest({ platform: "ios" }))
            ).json();
            expect(mockGetTouringScarcityRails).not.toHaveBeenCalled();
            expect(mockGetFreshAndRisingRails).not.toHaveBeenCalled();
            expect(mockGetAffinityRails).not.toHaveBeenCalled();
            expect(mockGetClubs).toHaveBeenCalledOnce();
            expect(data.popularClubs).toEqual([{ id: 101 }]);
            expect(
                data.railPlan.rails.some(
                    (rail: any) => rail.railKey === "popular_clubs",
                ),
            ).toBe(false);
            assertResolvable(data);
        });

        it("invokes only the chosen dynamic rotation member and keeps every planned ID resolvable", async () => {
            const policy = getDefaultDiscoveryRailPolicy("ios");
            policy.rails = ["just_passing_through", "starting_to_buzz"].map(
                (railKey) => ({
                    railKey,
                    enabled: true,
                    position: 0,
                    rotationPool: "dynamic",
                    weight: 1,
                }),
            ) as typeof policy.rails;
            mockGetDiscoveryRailPolicy.mockResolvedValue(policy);
            const item = {
                show: { id: 111 },
                performer: { id: 11 },
                reason: { label: "Evidence" },
            };
            mockGetTouringScarcityRails.mockResolvedValue({
                justPassingThrough: {
                    railKey: "just_passing_through",
                    label: "Visitor",
                    items: [item],
                },
            } as never);
            mockGetFreshAndRisingRails.mockResolvedValue({
                startingToBuzz: {
                    railKey: "starting_to_buzz",
                    label: "Buzz",
                    items: [item],
                },
            } as never);
            const { data } = await (
                await GET(makeRequest({ platform: "ios" }))
            ).json();
            expect(
                mockGetTouringScarcityRails.mock.calls.length +
                    mockGetFreshAndRisingRails.mock.calls.length,
            ).toBe(1);
            expect(data.dynamicRails).toHaveLength(1);
            expect(data.railPlan.rails).toHaveLength(1);
            expect(data.dynamicRails[0].railKey).toBe(
                data.railPlan.rails[0].railKey,
            );
            assertResolvable(data);
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
                50,
            );
            expect(mockGetShowsNearZip).toHaveBeenCalledWith(
                "94108",
                50,
                undefined,
                50,
            );
            expect(mockGetClubsByZip).toHaveBeenCalledWith("94108", 50, 8, {
                requireImage: true,
            });
            expect(mockGetTrendingShowsThisWeek).toHaveBeenCalledWith(
                "UTC",
                "94108",
                50,
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
        it("preserves the diverse hero selection when nearby loaders return a larger chronological pool", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });
            const candidates = [1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9].map(
                (performerId, index) => ({
                    id: index + 1,
                    clubId: 1,
                    name: `Show ${index + 1}`,
                    imageUrl: "",
                    date: new Date(Date.UTC(2026, 8, 15, 18, index)),
                    lineup: [
                        {
                            id: performerId,
                            uuid: `comic-${performerId}`,
                            name: `Comic ${performerId}`,
                            imageUrl: "",
                        },
                    ],
                }),
            );
            mockGetShowsNearZip.mockResolvedValue(candidates);
            const response = await GET(makeRequest({ zip: "10001" }));
            const { data } = await response.json();

            expect(response.status).toBe(200);
            expect(
                data.hero.shows.map((item: { id: number }) => item.id),
            ).toEqual([1, 4, 5]);
            const nearbyIds = data.moreNearYou.map(
                (item: { id: number }) => item.id,
            );
            expect(nearbyIds).toEqual([2, 3, 6, 7, 8, 9, 10, 11]);
            expect(nearbyIds.some((id: number) => [1, 4, 5].includes(id))).toBe(
                false,
            );
            expect(candidates).toHaveLength(11);
        });

        it("puts the first 3 showsNearZip into hero.shows and the rest into moreNearYou", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });
            mockGetShowsNearZip.mockResolvedValue(
                [
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
                ].map((show) => ({
                    ...show,
                    date: new Date(Date.UTC(2026, 8, 15, 18, show.id)),
                })) as never,
            );

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
            mockGetShowsNearZip.mockResolvedValue(
                [{ id: 1 }, { id: 2 }].map((show) => ({
                    ...show,
                    date: new Date(Date.UTC(2026, 8, 15, 18, show.id)),
                })) as never,
            );

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
                null,
                25,
                50,
            );
            expect(body.data.followedComedianShows).toEqual([
                { id: 41, name: "Favorite Comic Night" },
            ]);
        });

        it("retains eligible personalized matches when sparse inventory overlaps other sections", async () => {
            mockResolveAuth.mockResolvedValue({
                profileId: "profile-1",
                userId: "user-1",
            });
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });
            mockGetShowsNearZip.mockResolvedValue(
                [{ id: 1 }, { id: 2 }].map((show) => ({
                    ...show,
                    date: new Date(Date.UTC(2026, 8, 15, 18, show.id)),
                })) as never,
            );
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

            expect(body.data.followedComedianShows).toEqual(
                [1, 2, 3, 4, 9].map((id) => ({ id })),
            );
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
                null,
                25,
                50,
            );
            expect(body.data.followedComedianShows).toEqual([]);
        });

        it.each(["web", "ios", "android"] as const)(
            "location-filters followed-comedian shows with the resolved ZIP and requested distance for %s",
            async (platform) => {
                mockResolveAuth.mockResolvedValue({
                    profileId: "profile-1",
                    userId: "user-1",
                });
                mockGetHeroContext.mockResolvedValue({
                    zipCode: "10801",
                    city: "New Rochelle",
                    state: "NY",
                });

                const res = await GET(
                    makeRequest({
                        platform,
                        zip: "10801",
                        distance: "50",
                    }),
                );

                expect(res.status).toBe(200);
                expect(mockGetFavoriteComedianShows).toHaveBeenCalledWith(
                    "profile-1",
                    "10801",
                    50,
                    50,
                );
            },
        );

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
                undefined,
                undefined,
                50,
            );
            expect(mockGetTrendingShowsThisWeek).toHaveBeenCalledWith(
                "America/Los_Angeles",
                undefined,
                undefined,
                50,
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
                50,
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
                50,
            );
        });

        it("defaults to UTC when X-Timezone is absent", async () => {
            await GET(makeRequest());

            expect(mockGetShowsTonight).toHaveBeenCalledWith(
                "UTC",
                undefined,
                undefined,
                50,
            );
            expect(mockGetTrendingShowsThisWeek).toHaveBeenCalledWith(
                "UTC",
                undefined,
                undefined,
                50,
            );
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

describe("feed performance headers", () => {
    it("reports fixed provider outcomes without request or response identifiers", async () => {
        const response = await GET(
            makeRequest(
                { zip: "10001", platform: "ios" },
                { Authorization: "Bearer secret" },
            ),
        );
        const header = response.headers.get("Server-Timing")!;
        expect(header).toMatch(/feed_total;dur=[0-9.]+;desc="success"/);
        expect(header).toMatch(/trending_comedians;dur=[0-9.]+;desc="success"/);
        expect(header).toContain('affinity;dur=0;desc="skipped"');
        expect(header).toContain('shows_near_zip;dur=0;desc="skipped"');
        expect(header.split(", ")).toHaveLength(16);
        expect(header).not.toMatch(/10001|secret|Bearer/);
    });

    it("observes primary and optional errors before their fallback hides rejection", async () => {
        mockGetTrendingComedians.mockRejectedValueOnce(new Error("primary"));
        mockGetPodcastEpisodeDiscovery.mockRejectedValueOnce(
            new Error("optional"),
        );
        const response = await GET(makeRequest());
        const header = response.headers.get("Server-Timing")!;
        expect(response.status).toBe(200);
        expect(header).toMatch(/trending_comedians;dur=[0-9.]+;desc="error"/);
        expect(header).toMatch(/podcast_episodes;dur=[0-9.]+;desc="error"/);
    });

    it("reports timeout exactly once even when a provider later succeeds", async () => {
        vi.useFakeTimers();
        let resolve!: (items: never[]) => void;
        mockGetPodcastEpisodeDiscovery.mockReturnValueOnce(
            new Promise((r) => {
                resolve = r;
            }),
        );
        const pending = GET(makeRequest());
        await vi.advanceTimersByTimeAsync(800);
        const response = await pending;
        const before = response.headers.get("Server-Timing")!;
        expect(before).toMatch(/podcast_episodes;dur=[0-9.]+;desc="timeout"/);
        resolve([]);
        await Promise.resolve();
        expect(response.headers.get("Server-Timing")).toBe(before);
        vi.useRealTimers();
    });
});
