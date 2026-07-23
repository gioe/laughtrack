import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db", () => ({
    db: {
        $executeRaw: vi.fn(() => Promise.resolve(1)),
        $transaction: vi.fn((operations: Promise<unknown>[]) =>
            Promise.all(operations),
        ),
    },
}));

import { db } from "@/lib/db";
import {
    buildDiscoveryFeatureSnapshotUpsert,
    computeDiscoveryFeatures,
    DISCOVERY_FEATURE_VERSION,
    DiscoveryActivityObservation,
    DiscoveryFeatureInput,
    getDiscoveryFeatureWindows,
    recomputeDiscoveryFeatureSnapshots,
} from "./features";

const AS_OF = new Date("2026-09-01T15:30:00Z");
const COVERAGE_START = new Date("2026-01-01T00:00:00Z");
const MIGRATION_SQL = readFileSync(
    resolve(
        process.cwd(),
        "prisma/migrations/20260723203000_add_discovery_show_feature_snapshots/migration.sql",
    ),
    "utf8",
);

type SqlLike = {
    strings: readonly string[];
    values: readonly unknown[];
};

function toPgliteQuery(query: SqlLike) {
    const values = query.values.map((value) =>
        value instanceof Date ? value.toISOString() : value,
    );
    const text = query.strings.reduce((sql, chunk, index) => {
        if (index >= values.length) return sql + chunk;
        return `${sql}${chunk}$${index + 1}`;
    }, "");
    return { text, values };
}

function activities(
    prefix: string,
    count: number,
    observedAt: Date,
): DiscoveryActivityObservation[] {
    return Array.from({ length: count }, (_, index) => ({
        actorKey: `${prefix}-${index}`,
        observedAt,
    }));
}

function input(
    overrides: Partial<DiscoveryFeatureInput> = {},
): DiscoveryFeatureInput {
    return {
        showId: 42,
        asOf: AS_OF,
        legacyPopularity: 0.8,
        showDate: new Date("2026-09-10T00:00:00Z"),
        ticketsSoldOut: false,
        hasPurchasePath: true,
        followerObservations: [],
        favoriteCreatedAt: [],
        impressions: [],
        detailEngagements: [],
        ticketIntents: [],
        discoveryCoverageStart: COVERAGE_START,
        favoriteCoverageStart: COVERAGE_START,
        ...overrides,
    };
}

afterEach(() => {
    vi.clearAllMocks();
});

describe("discovery feature windows", () => {
    it("uses complete UTC days for recent, baseline, and social windows", () => {
        expect(getDiscoveryFeatureWindows(AS_OF)).toEqual({
            baselineStart: new Date("2026-07-28T00:00:00.000Z"),
            recentStart: new Date("2026-08-25T00:00:00.000Z"),
            trailing28Start: new Date("2026-08-04T00:00:00.000Z"),
            socialBaselineStart: new Date("2026-07-07T00:00:00.000Z"),
            end: new Date("2026-09-01T00:00:00.000Z"),
        });
    });

    it("rejects invalid evaluation times", () => {
        expect(() => getDiscoveryFeatureWindows(new Date("invalid"))).toThrow(
            "asOf must be a valid date",
        );
    });
});

describe("computeDiscoveryFeatures", () => {
    it("emits separate bounded features and explicit evidence", () => {
        const recentImpressions = activities(
            "recent",
            20,
            new Date("2026-08-28T12:00:00Z"),
        );
        const result = computeDiscoveryFeatures(
            input({
                impressions: recentImpressions,
                detailEngagements: recentImpressions.slice(0, 5),
                favoriteCreatedAt: [
                    new Date("2026-08-29T00:00:00Z"),
                    new Date("2026-08-30T00:00:00Z"),
                ],
            }),
        );

        expect(result).toMatchObject({
            showId: 42,
            featureVersion: DISCOVERY_FEATURE_VERSION,
            prominence: 0.8,
            momentum: 0.25,
            availability: "available",
        });
        expect(result.growth).toBeGreaterThanOrEqual(0);
        expect(result.growth).toBeLessThanOrEqual(1);
        expect(result.confidence).toBeGreaterThanOrEqual(0);
        expect(result.confidence).toBeLessThanOrEqual(1);
        expect(result.evidence.behavior).toMatchObject({
            momentumWindow: "recent",
            recentImpressionActors: 20,
            recentDetailActors: 5,
            recentTicketIntentActors: 0,
            recentDemandActors: 5,
            recentDemandRate: 0.25,
        });
    });

    it("compares impression-normalized demand instead of rewarding exposure", () => {
        const baselineImpressions = activities(
            "baseline",
            20,
            new Date("2026-08-01T12:00:00Z"),
        );
        const recentImpressions = activities(
            "recent",
            40,
            new Date("2026-08-28T12:00:00Z"),
        );
        const result = computeDiscoveryFeatures(
            input({
                impressions: [...baselineImpressions, ...recentImpressions],
                detailEngagements: [
                    ...baselineImpressions.slice(0, 2),
                    ...recentImpressions.slice(0, 4),
                ],
            }),
        );

        expect(result.evidence.behavior).toMatchObject({
            recentImpressionActors: 40,
            baselineImpressionActors: 20,
            recentDemandActors: 4,
            baselineDemandActors: 2,
            recentDemandRate: 0.1,
            baselineDemandRate: 0.1,
            growth: 0,
        });
        expect(result.momentum).toBe(0.1);
        expect(result.growth).toBe(0.5);
    });

    it("does not turn impressions without actions into momentum or growth", () => {
        const result = computeDiscoveryFeatures(
            input({
                impressions: [
                    ...activities(
                        "baseline",
                        20,
                        new Date("2026-08-01T12:00:00Z"),
                    ),
                    ...activities(
                        "recent",
                        40,
                        new Date("2026-08-28T12:00:00Z"),
                    ),
                ],
            }),
        );

        expect(result.momentum).toBe(0);
        expect(result.evidence.behavior.growth).toBe(0);
        expect(result.growth).toBe(0.5);
    });

    it("deduplicates actors and keeps authenticated and anonymous namespaces distinct", () => {
        const observedAt = new Date("2026-08-28T12:00:00Z");
        const exposed = [
            ...activities("exposed", 18, observedAt),
            { actorKey: "p:shared", observedAt },
            { actorKey: "a:shared", observedAt },
            { actorKey: "p:shared", observedAt },
        ];
        const result = computeDiscoveryFeatures(
            input({
                impressions: exposed,
                detailEngagements: [
                    { actorKey: "p:shared", observedAt },
                    { actorKey: "p:shared", observedAt },
                    { actorKey: "a:shared", observedAt },
                    { actorKey: "not-exposed", observedAt },
                ],
            }),
        );

        expect(result.evidence.behavior.recentImpressionActors).toBe(20);
        expect(result.evidence.behavior.recentDemandActors).toBe(2);
        expect(result.momentum).toBe(0.1);
    });

    it("falls back to the trailing 28 days when the recent window is sparse", () => {
        const older = activities("older", 20, new Date("2026-08-10T12:00:00Z"));
        const recent = activities(
            "recent",
            5,
            new Date("2026-08-28T12:00:00Z"),
        );
        const result = computeDiscoveryFeatures(
            input({
                impressions: [...older, ...recent],
                ticketIntents: [...older.slice(0, 4), ...recent.slice(0, 1)],
            }),
        );

        expect(result.evidence.behavior.momentumWindow).toBe("trailing28");
        expect(result.momentum).toBe(0.2);
        expect(result.evidence.confidenceReasons).toContain(
            "sparse_recent_impressions",
        );
    });

    it("keeps missing history neutral while treating measured zero and unchanged social counts as evidence", () => {
        const noHistory = computeDiscoveryFeatures(
            input({
                discoveryCoverageStart: undefined,
                favoriteCoverageStart: undefined,
                followerObservations: [
                    {
                        comedianId: 1,
                        platform: "instagram",
                        followerCount: 10,
                        observedAt: new Date("2026-08-20T00:00:00Z"),
                    },
                ],
            }),
        );
        expect(noHistory.growth).toBe(0.5);
        expect(noHistory.evidence.confidenceReasons).toEqual(
            expect.arrayContaining([
                "incomplete_attribution_history",
                "missing_favorite_baseline",
                "missing_social_baseline",
            ]),
        );

        const measured = computeDiscoveryFeatures(
            input({
                followerObservations: [
                    {
                        comedianId: 1,
                        platform: "youtube",
                        followerCount: 0,
                        observedAt: new Date("2026-07-15T00:00:00Z"),
                    },
                    {
                        comedianId: 1,
                        platform: "youtube",
                        followerCount: 0,
                        observedAt: new Date("2026-08-20T00:00:00Z"),
                    },
                ],
            }),
        );
        expect(measured.evidence.social).toMatchObject({
            pairedSeries: 1,
            observedSeries: 1,
            growth: 0,
            confidence: 1,
        });
        expect(measured.growth).toBe(0.5);
    });

    it("caps extreme positive and negative growth deterministically", () => {
        const positive = computeDiscoveryFeatures(
            input({
                favoriteCreatedAt: Array.from(
                    { length: 100 },
                    (_, index) =>
                        new Date(
                            `2026-08-${String(25 + (index % 7)).padStart(2, "0")}T12:00:00Z`,
                        ),
                ),
            }),
        );
        const negative = computeDiscoveryFeatures(
            input({
                favoriteCreatedAt: Array.from(
                    { length: 100 },
                    (_, index) =>
                        new Date(
                            `2026-08-${String(1 + (index % 20)).padStart(2, "0")}T12:00:00Z`,
                        ),
                ),
            }),
        );

        expect(positive.evidence.favorites.growth).toBe(1);
        expect(positive.growth).toBe(1);
        expect(negative.evidence.favorites.growth).toBe(-1);
        expect(negative.growth).toBe(0);
    });

    it.each([
        {
            label: "available",
            overrides: {},
            expected: "available",
        },
        {
            label: "unknown",
            overrides: { hasPurchasePath: false },
            expected: "unknown",
        },
        {
            label: "sold out",
            overrides: { ticketsSoldOut: true },
            expected: "unavailable",
        },
        {
            label: "past",
            overrides: { showDate: new Date("2026-08-31T00:00:00Z") },
            expected: "unavailable",
        },
    ])("classifies $label inventory", ({ overrides, expected }) => {
        expect(computeDiscoveryFeatures(input(overrides)).availability).toBe(
            expected,
        );
    });

    it("uses legacy popularity only as the prominence input", () => {
        const low = computeDiscoveryFeatures(
            input({
                legacyPopularity: -10,
                followerObservations: [],
            }),
        );
        const high = computeDiscoveryFeatures(
            input({
                legacyPopularity: 10,
                followerObservations: [
                    {
                        comedianId: 1,
                        platform: "instagram",
                        followerCount: 1_000_000,
                        observedAt: new Date("2026-08-20T00:00:00Z"),
                    },
                ],
            }),
        );

        expect(low.prominence).toBe(0);
        expect(high.prominence).toBe(1);
        expect(high.evidence.social.growth).toBeNull();
    });

    it("returns identical snapshots for the same fixed input and as-of time", () => {
        const value = input({
            favoriteCreatedAt: [new Date("2026-08-28T12:00:00Z")],
        });

        expect(computeDiscoveryFeatures(value)).toEqual(
            computeDiscoveryFeatures(value),
        );
    });
});

describe("discovery feature snapshot persistence", () => {
    it("upserts one logical row for a fixed show, version, and as-of time", async () => {
        const fixtureDb = new PGlite();
        try {
            await fixtureDb.exec(`
                CREATE TABLE shows (
                    id INTEGER PRIMARY KEY
                );
                INSERT INTO shows (id) VALUES (42);
            `);
            await fixtureDb.exec(MIGRATION_SQL);

            const first = computeDiscoveryFeatures(input());
            const firstQuery = toPgliteQuery(
                buildDiscoveryFeatureSnapshotUpsert(first),
            );
            await fixtureDb.query(firstQuery.text, firstQuery.values);

            const changed = computeDiscoveryFeatures(
                input({ legacyPopularity: 0.3 }),
            );
            const changedQuery = toPgliteQuery(
                buildDiscoveryFeatureSnapshotUpsert(changed),
            );
            await fixtureDb.query(changedQuery.text, changedQuery.values);

            const result = await fixtureDb.query<{
                row_count: number;
                prominence: number;
                feature_version: string;
            }>(`
                SELECT
                    COUNT(*)::INTEGER AS row_count,
                    MAX(prominence) AS prominence,
                    MAX(feature_version) AS feature_version
                FROM discovery_show_feature_snapshots
            `);
            expect(result.rows).toEqual([
                {
                    row_count: 1,
                    prominence: 0.3,
                    feature_version: DISCOVERY_FEATURE_VERSION,
                },
            ]);
        } finally {
            await fixtureDb.close();
        }
    });

    it("computes and persists a batch through one transaction", async () => {
        const values = [input(), input({ showId: 43 })];

        await expect(
            recomputeDiscoveryFeatureSnapshots(values),
        ).resolves.toEqual(values.map(computeDiscoveryFeatures));
        expect(db.$executeRaw).toHaveBeenCalledTimes(2);
        expect(db.$transaction).toHaveBeenCalledTimes(1);
    });
});
