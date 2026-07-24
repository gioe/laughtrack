import { describe, expect, it, vi } from "vitest";
import {
    runDiscoveryFeatureSnapshotJob,
    type DiscoveryFeatureSnapshotJobDependencies,
} from "./featureSnapshotJob";
import type {
    DiscoveryFeatureInput,
    DiscoveryFeatureSnapshot,
} from "./features";

function input(showId: number): DiscoveryFeatureInput {
    return {
        showId,
        asOf: new Date("2026-09-01T00:00:00.000Z"),
        legacyPopularity: 0.5,
        showDate: new Date("2026-09-10T00:00:00.000Z"),
        ticketsSoldOut: false,
        hasPurchasePath: true,
        followerObservations: [],
        favoriteCreatedAt: [],
        impressions: [],
        detailEngagements: [],
        ticketIntents: [],
    };
}

describe("runDiscoveryFeatureSnapshotJob", () => {
    it("canonicalizes the as-of day so repeated runs upsert one logical snapshot", async () => {
        const stored = new Map<string, DiscoveryFeatureSnapshot>();
        const loadBatch = vi.fn(async ({ asOf }: { asOf: Date }) => ({
            inputs: [{ ...input(42), asOf }],
            stale: 1,
        }));
        const persistSnapshot = vi.fn(
            async (snapshot: DiscoveryFeatureSnapshot) => {
                stored.set(
                    `${snapshot.showId}:${snapshot.featureVersion}:${snapshot.asOf.toISOString()}`,
                    snapshot,
                );
            },
        );
        const dependencies = {
            loadBatch,
            persistSnapshot,
        } as DiscoveryFeatureSnapshotJobDependencies;

        await runDiscoveryFeatureSnapshotJob(
            { asOf: new Date("2026-09-01T02:00:00.000Z") },
            dependencies,
        );
        await runDiscoveryFeatureSnapshotJob(
            { asOf: new Date("2026-09-01T22:00:00.000Z") },
            dependencies,
        );

        expect(loadBatch).toHaveBeenNthCalledWith(1, {
            asOf: new Date("2026-09-01T00:00:00.000Z"),
            batchSize: 200,
        });
        expect(loadBatch).toHaveBeenNthCalledWith(2, {
            asOf: new Date("2026-09-01T00:00:00.000Z"),
            batchSize: 200,
        });
        expect(persistSnapshot).toHaveBeenCalledTimes(2);
        expect(stored.size).toBe(1);
    });

    it("continues after one show fails and reports remaining stale work", async () => {
        const logger = { info: vi.fn(), error: vi.fn() };
        const persistSnapshot = vi.fn(
            async (snapshot: DiscoveryFeatureSnapshot) => {
                if (snapshot.showId === 2) {
                    throw new Error("database unavailable");
                }
            },
        );

        const result = await runDiscoveryFeatureSnapshotJob(
            {
                asOf: new Date("2026-09-01T15:30:00.000Z"),
                logger,
            },
            {
                loadBatch: vi.fn(async ({ asOf }) => ({
                    inputs: [1, 2, 3].map((showId) => ({
                        ...input(showId),
                        asOf,
                    })),
                    stale: 5,
                })),
                persistSnapshot,
            },
        );

        expect(result).toEqual({
            asOf: "2026-09-01T00:00:00.000Z",
            processed: 3,
            succeeded: 2,
            failed: 1,
            stale: 3,
            failures: [{ showId: 2, error: "database unavailable" }],
        });
        expect(persistSnapshot).toHaveBeenCalledTimes(3);
        expect(logger.error).toHaveBeenCalledWith(
            "[discovery-feature-snapshots] show 2 failed: database unavailable",
        );
        expect(logger.info).toHaveBeenCalledWith(
            "[discovery-feature-snapshots] processed=3 succeeded=2 failed=1 stale=3 asOf=2026-09-01T00:00:00.000Z",
        );
    });

    it("rejects an invalid as-of time before loading data", async () => {
        const loadBatch = vi.fn();

        await expect(
            runDiscoveryFeatureSnapshotJob(
                { asOf: new Date("invalid") },
                {
                    loadBatch,
                    persistSnapshot: vi.fn(),
                },
            ),
        ).rejects.toThrow("asOf must be a valid date");
        expect(loadBatch).not.toHaveBeenCalled();
    });
});
