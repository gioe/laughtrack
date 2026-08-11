import { describe, expect, it, vi } from "vitest";
import {
    getDiscoveryRailCycleIndex,
    loadDiscoveryRailPolicyWithFallback,
    selectDiscoveryRailPlan,
    type DiscoveryRailPayloadMap,
} from "./railSelector";
import {
    getDefaultDiscoveryRailPolicy,
    type DiscoveryRailPolicyDto,
} from "./railPolicy";

function rotatingPolicy(version = 7): DiscoveryRailPolicyDto {
    return {
        platform: "web",
        catalogVersion: 5,
        version,
        cycleCadenceHours: 24,
        rails: [
            {
                railKey: "shows_tonight",
                enabled: true,
                position: 0,
                rotationPool: "lead",
                weight: 3,
            },
            {
                railKey: "trending_this_week",
                enabled: true,
                position: 0,
                rotationPool: "lead",
                weight: 1,
            },
            {
                railKey: "popular_clubs",
                enabled: true,
                position: 1,
                rotationPool: null,
                weight: 1,
            },
        ],
    };
}

const rotatingPayloads: DiscoveryRailPayloadMap = {
    shows_tonight: {
        payloadKey: "showsTonight",
        items: [{ id: 1 }],
    },
    trending_this_week: {
        payloadKey: "trendingThisWeek",
        items: [{ id: 2 }],
    },
    popular_clubs: {
        payloadKey: "popularClubs",
        items: [{ id: 3 }],
    },
};

describe("selectDiscoveryRailPlan", () => {
    it("is stable within a cycle and can rotate in a later cycle", () => {
        const policy = rotatingPolicy();
        const first = selectDiscoveryRailPlan({
            policy,
            actorKey: "profile:42",
            cycleIndex: 100,
            payloads: rotatingPayloads,
        });
        const repeated = selectDiscoveryRailPlan({
            policy,
            actorKey: "profile:42",
            cycleIndex: 100,
            payloads: rotatingPayloads,
        });

        expect(repeated).toEqual(first);

        const laterSelections = Array.from(
            { length: 32 },
            (_, offset) =>
                selectDiscoveryRailPlan({
                    policy,
                    actorKey: "profile:42",
                    cycleIndex: 101 + offset,
                    payloads: rotatingPayloads,
                }).rails[0]?.railKey,
        );
        expect(laterSelections).toContain(
            first.rails[0].railKey === "shows_tonight"
                ? "trending_this_week"
                : "shows_tonight",
        );
    });

    it("uses platform, actor, policy version, and cycle in rotation seeds", () => {
        const selections = new Set<string>();

        for (let index = 0; index < 64; index += 1) {
            selections.add(
                selectDiscoveryRailPlan({
                    policy: rotatingPolicy(7 + (index % 2)),
                    actorKey: `actor:${index}`,
                    cycleIndex: 200 + index,
                    payloads: rotatingPayloads,
                }).rails[0].railKey,
            );
        }

        expect(selections).toEqual(
            new Set(["shows_tonight", "trending_this_week"]),
        );
    });

    it("calculates stable UTC cycle windows from caller-supplied time", () => {
        const firstWindow = Date.UTC(2026, 7, 6, 0, 0, 0);

        expect(getDiscoveryRailCycleIndex(firstWindow, 24)).toBe(
            getDiscoveryRailCycleIndex(firstWindow + 23 * 60 * 60 * 1000, 24),
        );
        expect(
            getDiscoveryRailCycleIndex(firstWindow + 24 * 60 * 60 * 1000, 24),
        ).toBe(getDiscoveryRailCycleIndex(firstWindow, 24) + 1);
    });

    it("suppresses empty rails and deduplicates candidates", () => {
        const policy: DiscoveryRailPolicyDto = {
            platform: "web",
            catalogVersion: 5,
            version: 5,
            cycleCadenceHours: 24,
            rails: [
                {
                    railKey: "shows_tonight",
                    enabled: true,
                    position: 0,
                    rotationPool: null,
                    weight: 1,
                },
                {
                    railKey: "followed_comedian_shows",
                    enabled: true,
                    position: 1,
                    rotationPool: null,
                    weight: 1,
                },
                {
                    railKey: "trending_this_week",
                    enabled: true,
                    position: 2,
                    rotationPool: null,
                    weight: 1,
                },
                {
                    railKey: "nearby_shows",
                    enabled: true,
                    position: 3,
                    rotationPool: null,
                    weight: 1,
                },
                {
                    railKey: "popular_clubs",
                    enabled: true,
                    position: 4,
                    rotationPool: null,
                    weight: 1,
                },
            ],
        };
        const payloads: DiscoveryRailPayloadMap = {
            shows_tonight: {
                payloadKey: "showsTonight",
                items: [{ id: 1 }, { id: 2 }],
            },
            followed_comedian_shows: {
                payloadKey: "followedComedianShows",
                items: [{ id: "2" }, { id: 3 }],
            },
            trending_this_week: {
                payloadKey: "trendingThisWeek",
                items: [{ id: 1 }, { id: 3 }, { id: 4 }],
            },
            nearby_shows: {
                payloadKey: "moreNearYou",
                items: [{ id: 4 }, { id: 5 }],
            },
            popular_clubs: {
                payloadKey: "popularClubs",
                items: [{}, { id: null }],
            },
        };
        const payloadSnapshot = structuredClone(payloads);

        const plan = selectDiscoveryRailPlan({
            policy,
            actorKey: "anonymous:visitor-1",
            cycleIndex: 10,
            payloads,
        });

        expect(plan.rails).toEqual([
            {
                railKey: "shows_tonight",
                payloadKey: "showsTonight",
                position: 0,
                itemIds: ["1", "2"],
            },
            {
                railKey: "followed_comedian_shows",
                payloadKey: "followedComedianShows",
                position: 1,
                itemIds: ["3"],
            },
            {
                railKey: "trending_this_week",
                payloadKey: "trendingThisWeek",
                position: 2,
                itemIds: ["4"],
            },
            {
                railKey: "nearby_shows",
                payloadKey: "moreNearYou",
                position: 3,
                itemIds: ["5"],
            },
        ]);
        expect(payloads).toEqual(payloadSnapshot);
    });

    it("uses resolved policy priority to deduplicate dynamic show rails", () => {
        const payloads: DiscoveryRailPayloadMap = {
            starting_to_buzz: {
                payloadKey: "dynamicRails",
                items: [{ id: 41 }, { id: 42 }],
            },
            from_your_podcasts: {
                payloadKey: "dynamicRails",
                items: [{ id: 41 }, { id: 43 }],
            },
            just_passing_through: {
                payloadKey: "dynamicRails",
                items: [{ id: 41 }, { id: 42 }, { id: 43 }],
            },
        };
        const policyFor = (
            railKeys: DiscoveryRailPolicyDto["rails"][number]["railKey"][],
        ): DiscoveryRailPolicyDto => ({
            platform: "web",
            catalogVersion: 5,
            version: 9,
            cycleCadenceHours: 24,
            rails: railKeys.map((railKey, position) => ({
                railKey,
                enabled: true,
                position,
                rotationPool: null,
                weight: 1,
            })),
        });

        const freshFirst = selectDiscoveryRailPlan({
            policy: policyFor([
                "starting_to_buzz",
                "from_your_podcasts",
                "just_passing_through",
            ]),
            actorKey: "profile:dynamic",
            cycleIndex: 12,
            payloads,
        });
        expect(freshFirst.rails).toEqual([
            {
                railKey: "starting_to_buzz",
                payloadKey: "dynamicRails",
                position: 0,
                itemIds: ["41", "42"],
            },
            {
                railKey: "from_your_podcasts",
                payloadKey: "dynamicRails",
                position: 1,
                itemIds: ["43"],
            },
        ]);

        const touringFirst = selectDiscoveryRailPlan({
            policy: policyFor([
                "just_passing_through",
                "from_your_podcasts",
                "starting_to_buzz",
            ]),
            actorKey: "profile:dynamic",
            cycleIndex: 12,
            payloads,
        });
        expect(touringFirst.rails).toEqual([
            {
                railKey: "just_passing_through",
                payloadKey: "dynamicRails",
                position: 0,
                itemIds: ["41", "42", "43"],
            },
        ]);
    });
});

describe("loadDiscoveryRailPolicyWithFallback", () => {
    it("returns the loaded policy when loading succeeds", async () => {
        const policy = rotatingPolicy();
        const loader = vi.fn().mockResolvedValue(policy);

        await expect(
            loadDiscoveryRailPolicyWithFallback("web", loader),
        ).resolves.toBe(policy);
        expect(loader).toHaveBeenCalledWith("web");
    });

    it("returns an independent platform default when loading fails", async () => {
        const loader = vi.fn().mockRejectedValue(new Error("database down"));

        const fallback = await loadDiscoveryRailPolicyWithFallback(
            "ios",
            loader,
        );
        fallback.rails[0].enabled = false;

        expect(fallback.platform).toBe("ios");
        expect(getDefaultDiscoveryRailPolicy("ios").rails[0].enabled).toBe(
            true,
        );
    });
});
