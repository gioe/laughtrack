import { describe, expect, it } from "vitest";
import {
    DISCOVERY_RAIL_CATALOG,
    DISCOVERY_RAIL_CATALOG_VERSION,
    DISCOVERY_RAIL_DEFAULTS,
    DiscoveryRailPolicyUpdateSchema,
    getDefaultDiscoveryRailPolicy,
    parseDiscoveryRailPolicy,
} from "./railPolicy";

const dynamicKeys = [
    "just_passing_through",
    "starting_to_buzz",
    "because_you_follow_them",
    "from_your_podcasts",
] as const;

const expectedKeys = {
    web: [
        "followed_comedian_shows",
        "trending_comedians",
        "shows_tonight",
        "nearby_shows",
        "trending_this_week",
        "popular_clubs",
        ...dynamicKeys,
    ],
    ios: [
        "shows_tonight",
        "followed_comedian_shows",
        "trending_this_week",
        "trending_comedians",
        "popular_clubs",
        "trending_podcasts",
        ...dynamicKeys,
    ],
    android: [
        "shows_tonight",
        "trending_this_week",
        "followed_comedian_shows",
        "trending_comedians",
        "popular_clubs",
        "trending_podcasts",
        ...dynamicKeys,
    ],
} as const;

function update(
    overrides: Partial<{
        platform: "web" | "ios" | "android";
        catalogVersion: number;
        expectedVersion: number;
        cycleCadenceHours: number;
        rails: Array<{
            railKey: string;
            enabled: boolean;
            position: number;
            rotationPool: string | null;
            weight: number;
        }>;
    }> = {},
) {
    const policy = getDefaultDiscoveryRailPolicy("web");
    return {
        platform: policy.platform,
        catalogVersion: policy.catalogVersion,
        expectedVersion: policy.version,
        cycleCadenceHours: policy.cycleCadenceHours,
        rails: policy.rails,
        ...overrides,
    };
}

function messages(
    result: ReturnType<typeof DiscoveryRailPolicyUpdateSchema.safeParse>,
) {
    return result.success
        ? []
        : result.error.issues.map((issue) => issue.message);
}

describe("discovery rail catalog", () => {
    it("uses stable keys and declares content, auth, and platform metadata", () => {
        expect(DISCOVERY_RAIL_CATALOG_VERSION).toBe(4);
        expect(Object.keys(DISCOVERY_RAIL_CATALOG)).toEqual([
            "shows_tonight",
            "followed_comedian_shows",
            "trending_this_week",
            "trending_comedians",
            "popular_clubs",
            "trending_podcasts",
            "nearby_shows",
            "just_passing_through",
            "starting_to_buzz",
            "from_your_podcasts",
            "because_you_follow_them",
        ]);
        expect(DISCOVERY_RAIL_CATALOG.followed_comedian_shows).toMatchObject({
            contentKind: "show",
            requiresAuth: true,
            supportedPlatforms: ["web", "ios", "android"],
        });
        expect(
            DISCOVERY_RAIL_CATALOG.trending_podcasts.supportedPlatforms,
        ).toEqual(["ios", "android"]);
        expect(DISCOVERY_RAIL_CATALOG.nearby_shows.supportedPlatforms).toEqual([
            "web",
        ]);
        expect(DISCOVERY_RAIL_CATALOG.from_your_podcasts).toMatchObject({
            contentKind: "show",
            requiresAuth: true,
            supportedPlatforms: ["web", "ios", "android"],
        });
    });
});

describe("production-compatible defaults", () => {
    it.each(["web", "ios", "android"] as const)(
        "preserves the current %s rail order and appends dynamic rails",
        (platform) => {
            const policy = DISCOVERY_RAIL_DEFAULTS[platform];
            expect(policy).toMatchObject({
                platform,
                catalogVersion: 4,
                version: 4,
                cycleCadenceHours: 24,
            });
            expect(policy.rails.map((rail) => rail.railKey)).toEqual(
                expectedKeys[platform],
            );
            expect(policy.rails.map((rail) => rail.position)).toEqual([
                0, 1, 2, 3, 4, 5, 6, 7, 8, 8,
            ]);
            expect(
                policy.rails
                    .slice(0, 6)
                    .every(
                        (rail) =>
                            rail.enabled &&
                            rail.rotationPool === null &&
                            rail.weight === 1,
                    ),
            ).toBe(true);
            expect(policy.rails[6]).toMatchObject({
                railKey: "just_passing_through",
                position: 6,
                rotationPool: null,
                weight: 1,
            });
            expect(policy.rails[7]).toMatchObject({
                railKey: "starting_to_buzz",
                position: 7,
                rotationPool: null,
                weight: 1,
            });
            expect(
                policy.rails.slice(8).map((rail) => rail.rotationPool),
            ).toEqual(["affinity", "affinity"]);
            expect(
                policy.rails
                    .slice(8)
                    .every((rail) => rail.enabled && rail.weight === 1),
            ).toBe(true);
            expect(() => parseDiscoveryRailPolicy(policy)).not.toThrow();
        },
    );

    it("returns independent copies so request code cannot mutate defaults", () => {
        const first = getDefaultDiscoveryRailPolicy("web");
        first.rails[0].enabled = false;

        expect(getDefaultDiscoveryRailPolicy("web").rails[0].enabled).toBe(
            true,
        );
    });
});

describe("DiscoveryRailPolicyUpdateSchema", () => {
    it("accepts fixed slots and a weighted rotation slot", () => {
        const result = DiscoveryRailPolicyUpdateSchema.safeParse(
            update({
                rails: [
                    {
                        railKey: "shows_tonight",
                        enabled: true,
                        position: 0,
                        rotationPool: null,
                        weight: 1,
                    },
                    {
                        railKey: "trending_comedians",
                        enabled: true,
                        position: 1,
                        rotationPool: "discovery_mix",
                        weight: 70,
                    },
                    {
                        railKey: "popular_clubs",
                        enabled: false,
                        position: 1,
                        rotationPool: "discovery_mix",
                        weight: 30,
                    },
                ],
            }),
        );

        expect(result.success).toBe(true);
    });

    it("is strict and rejects unknown platforms and rail keys", () => {
        expect(
            DiscoveryRailPolicyUpdateSchema.safeParse({
                ...update(),
                extra: true,
            }).success,
        ).toBe(false);
        expect(
            DiscoveryRailPolicyUpdateSchema.safeParse(
                update({ platform: "windows" as "web" }),
            ).success,
        ).toBe(false);

        const rails = update().rails;
        rails[0] = { ...rails[0], railKey: "made_up" };
        expect(
            messages(
                DiscoveryRailPolicyUpdateSchema.safeParse(update({ rails })),
            ),
        ).toContain("Unknown discovery rail key: made_up");
    });

    it("rejects rails unsupported by the selected platform", () => {
        const rails = update().rails;
        rails[0] = { ...rails[0], railKey: "trending_podcasts" };

        expect(
            messages(
                DiscoveryRailPolicyUpdateSchema.safeParse(update({ rails })),
            ),
        ).toContain("trending_podcasts is not supported on web");
    });

    it("rejects duplicate rail keys and fixed positions", () => {
        const rails = update().rails;
        rails[1] = {
            ...rails[1],
            railKey: rails[0].railKey,
            position: rails[0].position,
        };
        const result = DiscoveryRailPolicyUpdateSchema.safeParse(
            update({ rails }),
        );

        expect(messages(result)).toContain(
            `Duplicate discovery rail key: ${rails[0].railKey}`,
        );
        expect(messages(result)).toContain(
            "Fixed position 0 is already occupied",
        );
    });

    it("rejects gaps and conflicting rotation pools", () => {
        const gapRails = update().rails.map((rail, index) =>
            index === 1 ? { ...rail, position: 8 } : rail,
        );
        expect(
            messages(
                DiscoveryRailPolicyUpdateSchema.safeParse(
                    update({ rails: gapRails }),
                ),
            ),
        ).toContain("Rail slot positions must be contiguous starting at 0");

        const poolRails = [
            {
                railKey: "shows_tonight",
                enabled: true,
                position: 0,
                rotationPool: "mix",
                weight: 1,
            },
            {
                railKey: "trending_this_week",
                enabled: true,
                position: 1,
                rotationPool: "mix",
                weight: 1,
            },
        ];
        expect(
            messages(
                DiscoveryRailPolicyUpdateSchema.safeParse(
                    update({ rails: poolRails }),
                ),
            ),
        ).toContain("Rotation pool mix must use one position");
    });

    it("rejects two pools in one slot and pools with no enabled member", () => {
        const rails = [
            {
                railKey: "shows_tonight",
                enabled: false,
                position: 0,
                rotationPool: "primary",
                weight: 50,
            },
            {
                railKey: "trending_this_week",
                enabled: false,
                position: 0,
                rotationPool: "secondary",
                weight: 50,
            },
        ];
        const result = DiscoveryRailPolicyUpdateSchema.safeParse(
            update({ rails }),
        );

        expect(messages(result)).toContain(
            "Position 0 is already occupied by another slot",
        );
        expect(messages(result)).toContain(
            "Rotation pool primary must have at least one enabled rail",
        );
        expect(messages(result)).toContain(
            "Rotation pool secondary must have at least one enabled rail",
        );
    });

    it("rejects invalid fixed and rotation weights", () => {
        const fixed = update().rails;
        fixed[0] = { ...fixed[0], weight: 2 };
        expect(
            messages(
                DiscoveryRailPolicyUpdateSchema.safeParse(
                    update({ rails: fixed }),
                ),
            ),
        ).toContain("Fixed rails must have weight 1");

        for (const weight of [0, 101, 1.5]) {
            const rails = update().rails;
            rails[0] = {
                ...rails[0],
                rotationPool: "mix",
                weight,
            };
            expect(
                DiscoveryRailPolicyUpdateSchema.safeParse(update({ rails }))
                    .success,
            ).toBe(false);
        }
    });

    it("rejects invalid cadence and catalog versions", () => {
        for (const cycleCadenceHours of [0, 169, 1.5]) {
            expect(
                DiscoveryRailPolicyUpdateSchema.safeParse(
                    update({ cycleCadenceHours }),
                ).success,
            ).toBe(false);
        }
        expect(
            DiscoveryRailPolicyUpdateSchema.safeParse(
                update({ catalogVersion: 1 }),
            ).success,
        ).toBe(false);
    });
});
