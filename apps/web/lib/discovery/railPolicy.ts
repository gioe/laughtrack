import { z } from "zod";

export const DISCOVERY_RAIL_CATALOG_VERSION = 3 as const;

export const DISCOVERY_PLATFORMS = ["web", "ios", "android"] as const;
export type DiscoveryPlatform = (typeof DISCOVERY_PLATFORMS)[number];

export const DISCOVERY_RAIL_KEYS = [
    "shows_tonight",
    "followed_comedian_shows",
    "trending_this_week",
    "trending_comedians",
    "popular_clubs",
    "trending_podcasts",
    "nearby_shows",
    "just_passing_through",
    "rare_returns",
    "only_chance_nearby",
    "newly_added",
    "starting_to_buzz",
    "catch_them_early",
    "from_your_podcasts",
    "because_you_follow_them",
] as const;
export type DiscoveryRailKey = (typeof DISCOVERY_RAIL_KEYS)[number];

export const DISCOVERY_RAIL_CONTENT_KINDS = [
    "show",
    "comedian",
    "club",
    "podcast",
] as const;
export type DiscoveryRailContentKind =
    (typeof DISCOVERY_RAIL_CONTENT_KINDS)[number];

export interface DiscoveryRailCatalogEntry {
    key: DiscoveryRailKey;
    label: string;
    contentKind: DiscoveryRailContentKind;
    requiresAuth: boolean;
    supportedPlatforms: readonly DiscoveryPlatform[];
}

const ALL_PLATFORMS: readonly DiscoveryPlatform[] = DISCOVERY_PLATFORMS;

export const DISCOVERY_RAIL_CATALOG = {
    shows_tonight: {
        key: "shows_tonight",
        label: "Shows tonight",
        contentKind: "show",
        requiresAuth: false,
        supportedPlatforms: ALL_PLATFORMS,
    },
    followed_comedian_shows: {
        key: "followed_comedian_shows",
        label: "Shows from followed comedians",
        contentKind: "show",
        requiresAuth: true,
        supportedPlatforms: ALL_PLATFORMS,
    },
    trending_this_week: {
        key: "trending_this_week",
        label: "Trending this week",
        contentKind: "show",
        requiresAuth: false,
        supportedPlatforms: ALL_PLATFORMS,
    },
    trending_comedians: {
        key: "trending_comedians",
        label: "Trending comedians",
        contentKind: "comedian",
        requiresAuth: false,
        supportedPlatforms: ALL_PLATFORMS,
    },
    popular_clubs: {
        key: "popular_clubs",
        label: "Popular clubs",
        contentKind: "club",
        requiresAuth: false,
        supportedPlatforms: ALL_PLATFORMS,
    },
    trending_podcasts: {
        key: "trending_podcasts",
        label: "Trending podcasts",
        contentKind: "podcast",
        requiresAuth: false,
        supportedPlatforms: ["ios", "android"],
    },
    nearby_shows: {
        key: "nearby_shows",
        label: "Nearby shows",
        contentKind: "show",
        requiresAuth: false,
        supportedPlatforms: ["web"],
    },
    just_passing_through: {
        key: "just_passing_through",
        label: "Just passing through",
        contentKind: "show",
        requiresAuth: false,
        supportedPlatforms: ALL_PLATFORMS,
    },
    rare_returns: {
        key: "rare_returns",
        label: "Rarely in town / Back after a while",
        contentKind: "show",
        requiresAuth: false,
        supportedPlatforms: ALL_PLATFORMS,
    },
    only_chance_nearby: {
        key: "only_chance_nearby",
        label: "Only chance nearby",
        contentKind: "show",
        requiresAuth: false,
        supportedPlatforms: ALL_PLATFORMS,
    },
    newly_added: {
        key: "newly_added",
        label: "Newly added",
        contentKind: "show",
        requiresAuth: false,
        supportedPlatforms: ALL_PLATFORMS,
    },
    starting_to_buzz: {
        key: "starting_to_buzz",
        label: "Starting to buzz",
        contentKind: "show",
        requiresAuth: false,
        supportedPlatforms: ALL_PLATFORMS,
    },
    catch_them_early: {
        key: "catch_them_early",
        label: "Catch them early",
        contentKind: "show",
        requiresAuth: false,
        supportedPlatforms: ALL_PLATFORMS,
    },
    from_your_podcasts: {
        key: "from_your_podcasts",
        label: "From your podcasts",
        contentKind: "show",
        requiresAuth: true,
        supportedPlatforms: ALL_PLATFORMS,
    },
    because_you_follow_them: {
        key: "because_you_follow_them",
        label: "Because you follow them",
        contentKind: "show",
        requiresAuth: true,
        supportedPlatforms: ALL_PLATFORMS,
    },
} as const satisfies Record<DiscoveryRailKey, DiscoveryRailCatalogEntry>;

export interface DiscoveryRailPolicyRailDto {
    railKey: DiscoveryRailKey;
    enabled: boolean;
    position: number;
    rotationPool: string | null;
    weight: number;
}

/** JSON-safe policy returned by admin APIs and consumed by feed planning. */
export interface DiscoveryRailPolicyDto {
    platform: DiscoveryPlatform;
    catalogVersion: typeof DISCOVERY_RAIL_CATALOG_VERSION;
    version: number;
    cycleCadenceHours: number;
    rails: DiscoveryRailPolicyRailDto[];
}

export interface DiscoveryRailPolicyUpdateDto {
    platform: DiscoveryPlatform;
    catalogVersion: typeof DISCOVERY_RAIL_CATALOG_VERSION;
    expectedVersion: number;
    cycleCadenceHours: number;
    rails: DiscoveryRailPolicyRailDto[];
}

function fixedRail(
    railKey: DiscoveryRailKey,
    position: number,
): DiscoveryRailPolicyRailDto {
    return {
        railKey,
        enabled: true,
        position,
        rotationPool: null,
        weight: 1,
    };
}

function rotatingRail(
    railKey: DiscoveryRailKey,
    position: number,
    rotationPool: string,
): DiscoveryRailPolicyRailDto {
    return {
        railKey,
        enabled: true,
        position,
        rotationPool,
        weight: 1,
    };
}

function dynamicRotationRails(): DiscoveryRailPolicyRailDto[] {
    return [
        rotatingRail("just_passing_through", 6, "touring_scarcity"),
        rotatingRail("only_chance_nearby", 6, "touring_scarcity"),
        rotatingRail("rare_returns", 6, "touring_scarcity"),
        rotatingRail("catch_them_early", 7, "fresh_and_rising"),
        rotatingRail("newly_added", 7, "fresh_and_rising"),
        rotatingRail("starting_to_buzz", 7, "fresh_and_rising"),
        rotatingRail("because_you_follow_them", 8, "affinity"),
        rotatingRail("from_your_podcasts", 8, "affinity"),
    ];
}

export const DISCOVERY_RAIL_DEFAULTS = {
    web: {
        platform: "web",
        catalogVersion: DISCOVERY_RAIL_CATALOG_VERSION,
        version: 3,
        cycleCadenceHours: 24,
        rails: [
            fixedRail("followed_comedian_shows", 0),
            fixedRail("trending_comedians", 1),
            fixedRail("shows_tonight", 2),
            fixedRail("nearby_shows", 3),
            fixedRail("trending_this_week", 4),
            fixedRail("popular_clubs", 5),
            ...dynamicRotationRails(),
        ],
    },
    ios: {
        platform: "ios",
        catalogVersion: DISCOVERY_RAIL_CATALOG_VERSION,
        version: 3,
        cycleCadenceHours: 24,
        rails: [
            fixedRail("shows_tonight", 0),
            fixedRail("followed_comedian_shows", 1),
            fixedRail("trending_this_week", 2),
            fixedRail("trending_comedians", 3),
            fixedRail("popular_clubs", 4),
            fixedRail("trending_podcasts", 5),
            ...dynamicRotationRails(),
        ],
    },
    android: {
        platform: "android",
        catalogVersion: DISCOVERY_RAIL_CATALOG_VERSION,
        version: 3,
        cycleCadenceHours: 24,
        rails: [
            fixedRail("shows_tonight", 0),
            fixedRail("trending_this_week", 1),
            fixedRail("followed_comedian_shows", 2),
            fixedRail("trending_comedians", 3),
            fixedRail("popular_clubs", 4),
            fixedRail("trending_podcasts", 5),
            ...dynamicRotationRails(),
        ],
    },
} as const satisfies Record<DiscoveryPlatform, DiscoveryRailPolicyDto>;

const platformSchema = z.enum(DISCOVERY_PLATFORMS);
const catalogVersionSchema = z.literal(DISCOVERY_RAIL_CATALOG_VERSION);
const railKeySchema = z.string().min(1);
const rotationPoolSchema = z
    .string()
    .trim()
    .min(1)
    .max(64)
    .regex(/^[a-z][a-z0-9_]*$/)
    .nullable();

const railSchema = z
    .object({
        railKey: railKeySchema,
        enabled: z.boolean(),
        position: z.number().int().min(0),
        rotationPool: rotationPoolSchema,
        weight: z.number().int().min(1).max(100),
    })
    .strict();

type RefinablePolicy = {
    platform: DiscoveryPlatform;
    rails: Array<z.infer<typeof railSchema>>;
};

function addPolicyIssues(value: RefinablePolicy, ctx: z.RefinementCtx): void {
    const seenKeys = new Set<string>();
    const fixedPositions = new Set<number>();
    const positionModes = new Map<number, string>();
    const pools = new Map<
        string,
        { position: number; enabledMembers: number }
    >();

    value.rails.forEach((rail, index) => {
        const catalogEntry =
            DISCOVERY_RAIL_CATALOG[
                rail.railKey as keyof typeof DISCOVERY_RAIL_CATALOG
            ];
        if (!catalogEntry) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                path: ["rails", index, "railKey"],
                message: `Unknown discovery rail key: ${rail.railKey}`,
            });
        } else if (
            !catalogEntry.supportedPlatforms.includes(value.platform as never)
        ) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                path: ["rails", index, "railKey"],
                message: `${rail.railKey} is not supported on ${value.platform}`,
            });
        }

        if (seenKeys.has(rail.railKey)) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                path: ["rails", index, "railKey"],
                message: `Duplicate discovery rail key: ${rail.railKey}`,
            });
        }
        seenKeys.add(rail.railKey);

        if (rail.rotationPool === null) {
            if (rail.weight !== 1) {
                ctx.addIssue({
                    code: z.ZodIssueCode.custom,
                    path: ["rails", index, "weight"],
                    message: "Fixed rails must have weight 1",
                });
            }
            if (fixedPositions.has(rail.position)) {
                ctx.addIssue({
                    code: z.ZodIssueCode.custom,
                    path: ["rails", index, "position"],
                    message: `Fixed position ${rail.position} is already occupied`,
                });
            }
            fixedPositions.add(rail.position);
            const existingMode = positionModes.get(rail.position);
            if (existingMode && existingMode !== "fixed") {
                ctx.addIssue({
                    code: z.ZodIssueCode.custom,
                    path: ["rails", index, "position"],
                    message: `Position ${rail.position} cannot mix fixed and rotation rails`,
                });
            }
            positionModes.set(rail.position, "fixed");
            return;
        }

        const existingPool = pools.get(rail.rotationPool);
        if (existingPool && existingPool.position !== rail.position) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                path: ["rails", index, "position"],
                message: `Rotation pool ${rail.rotationPool} must use one position`,
            });
        }
        pools.set(rail.rotationPool, {
            position: existingPool?.position ?? rail.position,
            enabledMembers:
                (existingPool?.enabledMembers ?? 0) + (rail.enabled ? 1 : 0),
        });

        const existingMode = positionModes.get(rail.position);
        const poolMode = `pool:${rail.rotationPool}`;
        if (existingMode && existingMode !== poolMode) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                path: ["rails", index, "position"],
                message: `Position ${rail.position} is already occupied by another slot`,
            });
        }
        positionModes.set(rail.position, poolMode);
    });

    for (const [pool, state] of pools) {
        if (state.enabledMembers === 0) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                path: ["rails"],
                message: `Rotation pool ${pool} must have at least one enabled rail`,
            });
        }
    }

    const positions = [...positionModes.keys()].sort((a, b) => a - b);
    positions.forEach((position, index) => {
        if (position !== index) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                path: ["rails"],
                message: "Rail slot positions must be contiguous starting at 0",
            });
        }
    });
}

export const DiscoveryRailPolicyUpdateSchema = z
    .object({
        platform: platformSchema,
        catalogVersion: catalogVersionSchema,
        expectedVersion: z.number().int().min(1),
        cycleCadenceHours: z.number().int().min(1).max(168),
        rails: z.array(railSchema).min(1),
    })
    .strict()
    .superRefine(addPolicyIssues);

export const DiscoveryRailPolicySchema = z
    .object({
        platform: platformSchema,
        catalogVersion: catalogVersionSchema,
        version: z.number().int().min(1),
        cycleCadenceHours: z.number().int().min(1).max(168),
        rails: z.array(railSchema).min(1),
    })
    .strict()
    .superRefine(addPolicyIssues);

export function getDefaultDiscoveryRailPolicy(
    platform: DiscoveryPlatform,
): DiscoveryRailPolicyDto {
    return structuredClone(DISCOVERY_RAIL_DEFAULTS[platform]);
}

export function parseDiscoveryRailPolicy(
    value: unknown,
): DiscoveryRailPolicyDto {
    return DiscoveryRailPolicySchema.parse(value) as DiscoveryRailPolicyDto;
}

export function parseDiscoveryRailPolicyUpdate(
    value: unknown,
): DiscoveryRailPolicyUpdateDto {
    return DiscoveryRailPolicyUpdateSchema.parse(
        value,
    ) as DiscoveryRailPolicyUpdateDto;
}
