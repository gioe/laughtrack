import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const HERE = dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = resolve(HERE, "../..");
const MIGRATION_SQL = readFileSync(
    resolve(
        WEB_ROOT,
        "prisma/migrations/20260806193000_add_discovery_rail_policies/migration.sql",
    ),
    "utf8",
);
const DYNAMIC_MIGRATION_SQL = readFileSync(
    resolve(
        WEB_ROOT,
        "prisma/migrations/20260807143000_add_dynamic_discovery_rails/migration.sql",
    ),
    "utf8",
);
const REMOVE_STACKED_LINEUPS_MIGRATION_SQL = readFileSync(
    resolve(
        WEB_ROOT,
        "prisma/migrations/20260809013000_remove_stacked_lineups_discovery_rail/migration.sql",
    ),
    "utf8",
);
const MERGE_RARELY_NEARBY_MIGRATION_SQL = readFileSync(
    resolve(
        WEB_ROOT,
        "prisma/migrations/20260810120000_merge_rarely_nearby_rails/migration.sql",
    ),
    "utf8",
);
const REMOVE_DUPLICATE_FOLLOWED_RAIL_MIGRATION_SQL = readFileSync(
    resolve(
        WEB_ROOT,
        "prisma/migrations/20260811010000_remove_duplicate_followed_rail/migration.sql",
    ),
    "utf8",
);
const RENAME_RARELY_NEARBY_MIGRATION_SQL = readFileSync(
    resolve(
        WEB_ROOT,
        "prisma/migrations/20260817110000_rename_rarely_nearby_rail/migration.sql",
    ),
    "utf8",
);
const SCHEMA_TEXT = readFileSync(
    resolve(WEB_ROOT, "prisma/schema.prisma"),
    "utf8",
);

const BASE_SCHEMA_SQL = `
    CREATE TABLE user_profiles (id TEXT PRIMARY KEY);
`;

type PolicyRow = {
    platform: string;
    policy_version: number;
    catalog_version: number;
    cycle_cadence_hours: number;
};

type CatalogRow = {
    key: string;
    label: string;
    content_kind: string;
    requires_auth: boolean;
    supported_platforms: string[];
    catalog_version: number;
};

type EntryRow = {
    platform: string;
    rail_key: string;
    enabled: boolean;
    position: number;
    rotation_pool: string | null;
    weight: number;
};

describe("Discover rail policy migration", () => {
    let db: PGlite;

    beforeAll(async () => {
        db = new PGlite();
        await db.exec(BASE_SCHEMA_SQL);
        await db.exec(MIGRATION_SQL);
    });

    afterAll(async () => {
        await db.close();
    });

    it("keeps the Prisma models synchronized with the normalized tables", () => {
        expect(SCHEMA_TEXT).toContain("model DiscoveryRailCatalog");
        expect(SCHEMA_TEXT).toContain("model DiscoveryRailPlatformPolicy");
        expect(SCHEMA_TEXT).toContain("model DiscoveryRailPolicyEntry");
        expect(SCHEMA_TEXT).toContain(
            '@@map("discovery_rail_platform_policies")',
        );
        expect(SCHEMA_TEXT).toContain('@@map("discovery_rail_policy_entries")');
    });

    it("seeds independent version-one platform policies", async () => {
        const result = await db.query<PolicyRow>(`
            SELECT platform, policy_version, catalog_version, cycle_cadence_hours
            FROM discovery_rail_platform_policies
            ORDER BY platform
        `);

        expect(result.rows).toEqual([
            {
                platform: "android",
                policy_version: 1,
                catalog_version: 1,
                cycle_cadence_hours: 24,
            },
            {
                platform: "ios",
                policy_version: 1,
                catalog_version: 1,
                cycle_cadence_hours: 24,
            },
            {
                platform: "web",
                policy_version: 1,
                catalog_version: 1,
                cycle_cadence_hours: 24,
            },
        ]);
    });

    it("seeds versioned catalog metadata for the supported clients", async () => {
        const result = await db.query<CatalogRow>(`
            SELECT key, label, content_kind, requires_auth,
                   supported_platforms, catalog_version
            FROM discovery_rail_catalog
            ORDER BY key
        `);

        expect(result.rows).toEqual([
            {
                key: "followed_comedian_shows",
                label: "Shows from followed comedians",
                content_kind: "show",
                requires_auth: true,
                supported_platforms: ["web", "ios", "android"],
                catalog_version: 1,
            },
            {
                key: "nearby_shows",
                label: "Nearby shows",
                content_kind: "show",
                requires_auth: false,
                supported_platforms: ["web"],
                catalog_version: 1,
            },
            {
                key: "popular_clubs",
                label: "Popular clubs",
                content_kind: "club",
                requires_auth: false,
                supported_platforms: ["web", "ios", "android"],
                catalog_version: 1,
            },
            {
                key: "shows_tonight",
                label: "Shows tonight",
                content_kind: "show",
                requires_auth: false,
                supported_platforms: ["web", "ios", "android"],
                catalog_version: 1,
            },
            {
                key: "trending_comedians",
                label: "Trending comedians",
                content_kind: "comedian",
                requires_auth: false,
                supported_platforms: ["web", "ios", "android"],
                catalog_version: 1,
            },
            {
                key: "trending_podcasts",
                label: "Trending podcasts",
                content_kind: "podcast",
                requires_auth: false,
                supported_platforms: ["ios", "android"],
                catalog_version: 1,
            },
            {
                key: "trending_this_week",
                label: "Trending this week",
                content_kind: "show",
                requires_auth: false,
                supported_platforms: ["web", "ios", "android"],
                catalog_version: 1,
            },
        ]);
    });

    it("seeds the exact current fixed rail order for every platform", async () => {
        const catalog = await db.query<{ key: string }>(`
            SELECT key FROM discovery_rail_catalog ORDER BY key
        `);
        const result = await db.query<EntryRow>(`
            SELECT platform, rail_key, enabled, position, rotation_pool, weight
            FROM discovery_rail_policy_entries
            ORDER BY platform, position
        `);
        const entriesFor = (platform: string) =>
            result.rows.filter((entry) => entry.platform === platform);
        const keysFor = (platform: string) =>
            entriesFor(platform).map((entry) => entry.rail_key);

        expect(catalog.rows.map((rail) => rail.key)).toEqual([
            "followed_comedian_shows",
            "nearby_shows",
            "popular_clubs",
            "shows_tonight",
            "trending_comedians",
            "trending_podcasts",
            "trending_this_week",
        ]);

        expect(keysFor("web")).toEqual([
            "followed_comedian_shows",
            "trending_comedians",
            "shows_tonight",
            "nearby_shows",
            "trending_this_week",
            "popular_clubs",
        ]);
        expect(keysFor("ios")).toEqual([
            "shows_tonight",
            "followed_comedian_shows",
            "trending_this_week",
            "trending_comedians",
            "popular_clubs",
            "trending_podcasts",
        ]);
        expect(keysFor("android")).toEqual([
            "shows_tonight",
            "trending_this_week",
            "followed_comedian_shows",
            "trending_comedians",
            "popular_clubs",
            "trending_podcasts",
        ]);
        for (const platform of ["web", "ios", "android"]) {
            expect(entriesFor(platform).map((entry) => entry.position)).toEqual(
                [0, 1, 2, 3, 4, 5],
            );
        }
        expect(result.rows).toHaveLength(18);
        expect(result.rows.every((entry) => entry.enabled)).toBe(true);
        expect(result.rows.every((entry) => entry.rotation_pool === null)).toBe(
            true,
        );
        expect(result.rows.every((entry) => entry.weight === 1)).toBe(true);
    });

    it("enforces platforms, catalog keys, positions, weights, and fixed-position uniqueness", async () => {
        await expect(
            db.query(`
                INSERT INTO discovery_rail_platform_policies (platform)
                VALUES ('desktop')
            `),
        ).rejects.toThrow();
        await expect(
            db.query(`
                INSERT INTO discovery_rail_policy_entries
                    (platform, rail_key, enabled, position, weight)
                VALUES ('web', 'unknown_rail', true, 20, 1)
            `),
        ).rejects.toThrow();
        await expect(
            db.query(`
                UPDATE discovery_rail_policy_entries
                SET position = -1
                WHERE platform = 'web' AND rail_key = 'shows_tonight'
            `),
        ).rejects.toThrow();
        await expect(
            db.query(`
                UPDATE discovery_rail_policy_entries
                SET weight = 101
                WHERE platform = 'web' AND rail_key = 'shows_tonight'
            `),
        ).rejects.toThrow();
        await expect(
            db.query(`
                UPDATE discovery_rail_policy_entries
                SET position = 0
                WHERE platform = 'web' AND rail_key = 'shows_tonight'
            `),
        ).rejects.toThrow();

        const indexes = await db.query<{ indexname: string }>(`
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'discovery_rail_policy_entries'
        `);
        expect(indexes.rows.map((row) => row.indexname)).toContain(
            "discovery_rail_policy_entries_fixed_position_key",
        );
    });

    it("cascades policy entries but restricts deletion of cataloged rails in use", async () => {
        await expect(
            db.query(
                "DELETE FROM discovery_rail_catalog WHERE key = 'shows_tonight'",
            ),
        ).rejects.toThrow();

        await db.exec("BEGIN");
        try {
            await db.query(
                "DELETE FROM discovery_rail_platform_policies WHERE platform = 'android'",
            );
            const remaining = await db.query<{ count: string }>(`
                SELECT COUNT(*)::text AS count
                FROM discovery_rail_policy_entries
                WHERE platform = 'android'
            `);
            expect(remaining.rows[0].count).toBe("0");
        } finally {
            await db.exec("ROLLBACK");
        }
    });
});

describe("dynamic Discover rail policy migration", () => {
    let db: PGlite;

    beforeAll(async () => {
        db = new PGlite();
        await db.exec(BASE_SCHEMA_SQL);
        await db.exec(MIGRATION_SQL);
        await db.query(`
            UPDATE discovery_rail_policy_entries
            SET enabled = false
            WHERE platform = 'web'
              AND rail_key = 'followed_comedian_shows'
        `);
        await db.exec(DYNAMIC_MIGRATION_SQL);
    });

    afterAll(async () => {
        await db.close();
    });

    it("adds the version-two dynamic catalog with correct auth metadata", async () => {
        const result = await db.query<{
            key: string;
            requires_auth: boolean;
            catalog_version: number;
        }>(`
            SELECT key, requires_auth, catalog_version
            FROM discovery_rail_catalog
            WHERE catalog_version = 2
            ORDER BY key
        `);

        expect(result.rows).toEqual([
            {
                key: "because_you_follow_them",
                requires_auth: true,
                catalog_version: 2,
            },
            {
                key: "catch_them_early",
                requires_auth: false,
                catalog_version: 2,
            },
            {
                key: "from_your_podcasts",
                requires_auth: true,
                catalog_version: 2,
            },
            {
                key: "just_passing_through",
                requires_auth: false,
                catalog_version: 2,
            },
            {
                key: "newly_added",
                requires_auth: false,
                catalog_version: 2,
            },
            {
                key: "only_chance_nearby",
                requires_auth: false,
                catalog_version: 2,
            },
            {
                key: "rare_returns",
                requires_auth: false,
                catalog_version: 2,
            },
            {
                key: "stacked_lineups",
                requires_auth: false,
                catalog_version: 2,
            },
            {
                key: "starting_to_buzz",
                requires_auth: false,
                catalog_version: 2,
            },
        ]);
    });

    it("appends enabled rotation families without replacing stored entries", async () => {
        const policies = await db.query<PolicyRow>(`
            SELECT platform, policy_version, catalog_version, cycle_cadence_hours
            FROM discovery_rail_platform_policies
            ORDER BY platform
        `);
        expect(
            policies.rows.map(
                ({ platform, policy_version, catalog_version }) => ({
                    platform,
                    policy_version,
                    catalog_version,
                }),
            ),
        ).toEqual([
            { platform: "android", policy_version: 2, catalog_version: 2 },
            { platform: "ios", policy_version: 2, catalog_version: 2 },
            { platform: "web", policy_version: 2, catalog_version: 2 },
        ]);

        const preserved = await db.query<{ enabled: boolean }>(`
            SELECT enabled
            FROM discovery_rail_policy_entries
            WHERE platform = 'web'
              AND rail_key = 'followed_comedian_shows'
        `);
        expect(preserved.rows).toEqual([{ enabled: false }]);

        const dynamic = await db.query<EntryRow>(`
            SELECT platform, rail_key, enabled, position, rotation_pool, weight
            FROM discovery_rail_policy_entries
            WHERE rotation_pool IS NOT NULL
            ORDER BY platform, position, rail_key
        `);
        expect(dynamic.rows).toHaveLength(27);
        for (const platform of ["android", "ios", "web"]) {
            const entries = dynamic.rows.filter(
                (entry) => entry.platform === platform,
            );
            expect(entries.map((entry) => entry.position)).toEqual([
                6, 6, 6, 7, 7, 7, 8, 8, 8,
            ]);
            expect(entries.map((entry) => entry.rotation_pool)).toEqual([
                "touring_scarcity",
                "touring_scarcity",
                "touring_scarcity",
                "fresh_and_rising",
                "fresh_and_rising",
                "fresh_and_rising",
                "affinity",
                "affinity",
                "affinity",
            ]);
            expect(entries.every((entry) => entry.enabled)).toBe(true);
            expect(entries.every((entry) => entry.weight === 1)).toBe(true);
        }
    });
});

describe("stacked lineups removal migration", () => {
    let db: PGlite;

    beforeAll(async () => {
        db = new PGlite();
        await db.exec(BASE_SCHEMA_SQL);
        await db.exec(MIGRATION_SQL);
        await db.exec(DYNAMIC_MIGRATION_SQL);
        await db.exec(REMOVE_STACKED_LINEUPS_MIGRATION_SQL);
    });

    afterAll(async () => {
        await db.close();
    });

    it("removes the rail from the catalog and every platform policy", async () => {
        const catalog = await db.query<{ count: string }>(`
            SELECT COUNT(*)::text AS count
            FROM discovery_rail_catalog
            WHERE key = 'stacked_lineups'
        `);
        const entries = await db.query<{ count: string }>(`
            SELECT COUNT(*)::text AS count
            FROM discovery_rail_policy_entries
            WHERE rail_key = 'stacked_lineups'
        `);
        const policies = await db.query<PolicyRow>(`
            SELECT platform, policy_version, catalog_version, cycle_cadence_hours
            FROM discovery_rail_platform_policies
            ORDER BY platform
        `);

        expect(catalog.rows[0].count).toBe("0");
        expect(entries.rows[0].count).toBe("0");
        expect(
            policies.rows.map(
                ({ platform, policy_version, catalog_version }) => ({
                    platform,
                    policy_version,
                    catalog_version,
                }),
            ),
        ).toEqual([
            { platform: "android", policy_version: 3, catalog_version: 3 },
            { platform: "ios", policy_version: 3, catalog_version: 3 },
            { platform: "web", policy_version: 3, catalog_version: 3 },
        ]);
    });
});

describe("Rarely nearby rail merge migration", () => {
    let db: PGlite;

    beforeAll(async () => {
        db = new PGlite();
        await db.exec(BASE_SCHEMA_SQL);
        await db.exec(MIGRATION_SQL);
        await db.exec(DYNAMIC_MIGRATION_SQL);
        await db.exec(REMOVE_STACKED_LINEUPS_MIGRATION_SQL);
        await db.exec(MERGE_RARELY_NEARBY_MIGRATION_SQL);
    });

    afterAll(async () => {
        await db.close();
    });

    it("retires consolidated rails and fixes both survivors in place", async () => {
        const retiredCatalog = await db.query<{ count: string }>(`
            SELECT COUNT(*)::text AS count
            FROM discovery_rail_catalog
            WHERE key IN (
                'rare_returns',
                'only_chance_nearby',
                'newly_added',
                'catch_them_early'
            )
        `);
        const retiredEntries = await db.query<{ count: string }>(`
            SELECT COUNT(*)::text AS count
            FROM discovery_rail_policy_entries
            WHERE rail_key IN (
                'rare_returns',
                'only_chance_nearby',
                'newly_added',
                'catch_them_early'
            )
        `);
        const survivingRail = await db.query<{
            label: string;
            catalog_version: number;
        }>(`
            SELECT label, catalog_version
            FROM discovery_rail_catalog
            WHERE key IN ('just_passing_through', 'starting_to_buzz')
            ORDER BY key
        `);
        const survivingEntries = await db.query<EntryRow>(`
            SELECT platform, rail_key, enabled, position, rotation_pool, weight
            FROM discovery_rail_policy_entries
            WHERE rail_key IN ('just_passing_through', 'starting_to_buzz')
            ORDER BY platform, position
        `);
        const policies = await db.query<PolicyRow>(`
            SELECT platform, policy_version, catalog_version, cycle_cadence_hours
            FROM discovery_rail_platform_policies
            ORDER BY platform
        `);

        expect(retiredCatalog.rows[0].count).toBe("0");
        expect(retiredEntries.rows[0].count).toBe("0");
        expect(survivingRail.rows).toEqual([
            { label: "Rarely nearby", catalog_version: 4 },
            { label: "Shows gaining momentum", catalog_version: 4 },
        ]);
        expect(survivingEntries.rows).toEqual(
            ["android", "ios", "web"].flatMap((platform) => [
                {
                    platform,
                    rail_key: "just_passing_through",
                    enabled: true,
                    position: 6,
                    rotation_pool: null,
                    weight: 1,
                },
                {
                    platform,
                    rail_key: "starting_to_buzz",
                    enabled: true,
                    position: 7,
                    rotation_pool: null,
                    weight: 1,
                },
            ]),
        );
        expect(
            policies.rows.map(
                ({ platform, policy_version, catalog_version }) => ({
                    platform,
                    policy_version,
                    catalog_version,
                }),
            ),
        ).toEqual([
            { platform: "android", policy_version: 4, catalog_version: 4 },
            { platform: "ios", policy_version: 4, catalog_version: 4 },
            { platform: "web", policy_version: 4, catalog_version: 4 },
        ]);
    });
});

describe("duplicate followed-comedian rail removal migration", () => {
    let db: PGlite;

    beforeAll(async () => {
        db = new PGlite();
        await db.exec(BASE_SCHEMA_SQL);
        await db.exec(MIGRATION_SQL);
        await db.exec(DYNAMIC_MIGRATION_SQL);
        await db.exec(REMOVE_STACKED_LINEUPS_MIGRATION_SQL);
        await db.exec(MERGE_RARELY_NEARBY_MIGRATION_SQL);
        await db.exec(`
            CREATE TABLE discovery_impression_events (
                id BIGSERIAL PRIMARY KEY,
                surface TEXT NOT NULL,
                CONSTRAINT discovery_impression_events_surface_check CHECK (
                    surface IN ('because_you_follow_them', 'followed_comedian_shows')
                )
            );
            INSERT INTO discovery_impression_events (surface)
            VALUES ('because_you_follow_them');
        `);
        await db.exec(REMOVE_DUPLICATE_FOLLOWED_RAIL_MIGRATION_SQL);
    });

    afterAll(async () => {
        await db.close();
    });

    it("removes the duplicate rail and makes the remaining affinity rail fixed", async () => {
        const retiredCatalog = await db.query<{ count: string }>(`
            SELECT COUNT(*)::text AS count
            FROM discovery_rail_catalog
            WHERE key = 'because_you_follow_them'
        `);
        const retiredEntries = await db.query<{ count: string }>(`
            SELECT COUNT(*)::text AS count
            FROM discovery_rail_policy_entries
            WHERE rail_key = 'because_you_follow_them'
        `);
        const podcastEntries = await db.query<EntryRow>(`
            SELECT platform, rail_key, enabled, position, rotation_pool, weight
            FROM discovery_rail_policy_entries
            WHERE rail_key = 'from_your_podcasts'
            ORDER BY platform
        `);

        expect(retiredCatalog.rows[0].count).toBe("0");
        expect(retiredEntries.rows[0].count).toBe("0");
        expect(podcastEntries.rows).toEqual(
            ["android", "ios", "web"].map((platform) => ({
                platform,
                rail_key: "from_your_podcasts",
                enabled: true,
                position: 8,
                rotation_pool: null,
                weight: 1,
            })),
        );
    });

    it("bumps persisted policies to version five and retires the impression surface", async () => {
        const policies = await db.query<PolicyRow>(`
            SELECT platform, policy_version, catalog_version, cycle_cadence_hours
            FROM discovery_rail_platform_policies
            ORDER BY platform
        `);

        expect(
            policies.rows.map(
                ({ platform, policy_version, catalog_version }) => ({
                    platform,
                    policy_version,
                    catalog_version,
                }),
            ),
        ).toEqual([
            { platform: "android", policy_version: 5, catalog_version: 5 },
            { platform: "ios", policy_version: 5, catalog_version: 5 },
            { platform: "web", policy_version: 5, catalog_version: 5 },
        ]);
        await expect(
            db.query(`
                INSERT INTO discovery_impression_events (surface)
                VALUES ('because_you_follow_them')
            `),
        ).rejects.toThrow();
        const retiredImpressions = await db.query<{ count: string }>(`
            SELECT COUNT(*)::text AS count
            FROM discovery_impression_events
            WHERE surface = 'because_you_follow_them'
        `);
        expect(retiredImpressions.rows[0].count).toBe("0");
        await expect(
            db.query(`
                INSERT INTO discovery_impression_events (surface)
                VALUES ('followed_comedian_shows')
            `),
        ).resolves.toBeDefined();
    });
});

describe("Here for a Limited Time rail rename migration", () => {
    let db: PGlite;

    beforeAll(async () => {
        db = new PGlite();
        await db.exec(BASE_SCHEMA_SQL);
        await db.exec(MIGRATION_SQL);
        await db.exec(DYNAMIC_MIGRATION_SQL);
        await db.exec(REMOVE_STACKED_LINEUPS_MIGRATION_SQL);
        await db.exec(MERGE_RARELY_NEARBY_MIGRATION_SQL);
        await db.exec(`
            CREATE TABLE discovery_impression_events (
                id BIGSERIAL PRIMARY KEY,
                surface TEXT NOT NULL,
                CONSTRAINT discovery_impression_events_surface_check CHECK (
                    surface IN ('because_you_follow_them', 'followed_comedian_shows')
                )
            );
        `);
        await db.exec(REMOVE_DUPLICATE_FOLLOWED_RAIL_MIGRATION_SQL);
        await db.exec(RENAME_RARELY_NEARBY_MIGRATION_SQL);
    });

    afterAll(async () => {
        await db.close();
    });

    it("renames the catalog entry and advances every platform policy", async () => {
        const catalog = await db.query<{
            label: string;
            catalog_version: number;
        }>(`
            SELECT label, catalog_version
            FROM discovery_rail_catalog
            WHERE key = 'just_passing_through'
        `);
        const policies = await db.query<PolicyRow>(`
            SELECT platform, policy_version, catalog_version, cycle_cadence_hours
            FROM discovery_rail_platform_policies
            ORDER BY platform
        `);

        expect(catalog.rows).toEqual([
            { label: "Here for a Limited Time", catalog_version: 6 },
        ]);
        expect(
            policies.rows.map(
                ({ platform, policy_version, catalog_version }) => ({
                    platform,
                    policy_version,
                    catalog_version,
                }),
            ),
        ).toEqual([
            { platform: "android", policy_version: 6, catalog_version: 6 },
            { platform: "ios", policy_version: 6, catalog_version: 6 },
            { platform: "web", policy_version: 6, catalog_version: 6 },
        ]);
    });
});
