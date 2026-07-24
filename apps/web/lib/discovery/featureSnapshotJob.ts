import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import { AVAILABLE_SHOW_WHERE } from "@/lib/data/show/showSelect";
import {
    buildDiscoveryFeatureSnapshotUpsert,
    computeDiscoveryFeatures,
    DISCOVERY_FEATURE_VERSION,
    getDiscoveryFeatureWindows,
    type DiscoveryActivityObservation,
    type DiscoveryFeatureInput,
    type DiscoveryFeatureSnapshot,
    type DiscoveryFollowerObservation,
} from "./features";

const DAY_MS = 24 * 60 * 60 * 1000;
const SNAPSHOT_HORIZON_DAYS = 30;
const DEFAULT_BATCH_SIZE = 200;
const MAX_BATCH_SIZE = 500;
const PERSIST_CONCURRENCY = 5;
const DISCOVERY_SURFACE = "near_you";
const SHOW_ENTITY_TYPE = "show";
const DETAIL_ENGAGEMENT_TYPE = "show_detail";

type SnapshotJobLogger = Pick<Console, "info" | "error">;

interface TicketIntentRow {
    showId: number;
    profileId: string | null;
    anonymousVisitorId: string;
    observedAt: Date;
}

interface EffectiveComedian {
    id: number;
    uuid: string;
}

export interface DiscoveryFeatureInputBatch {
    inputs: DiscoveryFeatureInput[];
    stale: number;
}

export interface DiscoveryFeatureSnapshotJobFailure {
    showId: number;
    error: string;
}

export interface DiscoveryFeatureSnapshotJobResult {
    asOf: string;
    processed: number;
    succeeded: number;
    failed: number;
    stale: number;
    failures: DiscoveryFeatureSnapshotJobFailure[];
}

export interface DiscoveryFeatureSnapshotJobOptions {
    asOf?: Date;
    batchSize?: number;
    logger?: SnapshotJobLogger;
}

export interface DiscoveryFeatureSnapshotJobDependencies {
    loadBatch: (options: {
        asOf: Date;
        batchSize: number;
    }) => Promise<DiscoveryFeatureInputBatch>;
    persistSnapshot: (snapshot: DiscoveryFeatureSnapshot) => Promise<void>;
}

function actorKey(
    profileId: string | null,
    anonymousVisitorId: string,
): string {
    return profileId
        ? `profile:${profileId}`
        : `anonymous:${anonymousVisitorId}`;
}

function pushByShowId<T>(
    target: Map<number, T[]>,
    showId: number,
    value: T,
): void {
    const values = target.get(showId) ?? [];
    values.push(value);
    target.set(showId, values);
}

function effectiveComedians(
    lineupItems: readonly {
        comedian: {
            id: number;
            uuid: string;
            parentComedian: {
                id: number;
                uuid: string;
                visible: boolean;
            } | null;
        };
    }[],
): EffectiveComedian[] {
    const byId = new Map<number, EffectiveComedian>();
    for (const { comedian } of lineupItems) {
        const effective =
            comedian.parentComedian?.visible === true
                ? comedian.parentComedian
                : comedian;
        byId.set(effective.id, { id: effective.id, uuid: effective.uuid });
    }
    return [...byId.values()];
}

function normalizeBatchSize(value: number | undefined): number {
    if (!Number.isFinite(value)) return DEFAULT_BATCH_SIZE;
    return Math.min(MAX_BATCH_SIZE, Math.max(1, Math.trunc(value as number)));
}

export function canonicalDiscoveryFeatureAsOf(value: Date): Date {
    if (Number.isNaN(value.getTime())) {
        throw new RangeError("asOf must be a valid date");
    }
    return getDiscoveryFeatureWindows(value).end;
}

export async function loadDiscoveryFeatureInputBatch({
    asOf,
    batchSize,
}: {
    asOf: Date;
    batchSize: number;
}): Promise<DiscoveryFeatureInputBatch> {
    const horizonEnd = new Date(
        asOf.getTime() + SNAPSHOT_HORIZON_DAYS * DAY_MS,
    );
    const staleWhere: Prisma.ShowWhereInput = {
        AND: [
            { club: { visible: true } },
            AVAILABLE_SHOW_WHERE,
            { date: { gt: asOf, lte: horizonEnd } },
            {
                discoveryFeatureSnapshots: {
                    none: {
                        featureVersion: DISCOVERY_FEATURE_VERSION,
                        asOf,
                    },
                },
            },
        ],
    };
    const [stale, shows] = await Promise.all([
        db.show.count({ where: staleWhere }),
        db.show.findMany({
            where: staleWhere,
            select: {
                id: true,
                popularity: true,
                date: true,
                ticketsSoldOut: true,
                tickets: {
                    where: { soldOut: false },
                    select: { purchaseUrl: true },
                },
                lineupItems: {
                    where: {
                        comedian: {
                            visible: true,
                            taggedComedians: {
                                none: { tag: { userFacing: false } },
                            },
                        },
                    },
                    select: {
                        comedian: {
                            select: {
                                id: true,
                                uuid: true,
                                parentComedian: {
                                    select: {
                                        id: true,
                                        uuid: true,
                                        visible: true,
                                    },
                                },
                            },
                        },
                    },
                },
            },
            orderBy: [{ date: "asc" }, { id: "asc" }],
            take: batchSize,
        }),
    ]);
    if (shows.length === 0) return { inputs: [], stale };

    const showIds = shows.map(({ id }) => id);
    const comediansByShowId = new Map(
        shows.map((show) => [show.id, effectiveComedians(show.lineupItems)]),
    );
    const comedianIds = [
        ...new Set([...comediansByShowId.values()].flat().map(({ id }) => id)),
    ];
    const comedianUuids = [
        ...new Set(
            [...comediansByShowId.values()].flat().map(({ uuid }) => uuid),
        ),
    ];
    const windows = getDiscoveryFeatureWindows(asOf);

    const [
        followers,
        favorites,
        impressions,
        details,
        ticketIntents,
        discoveryCoverage,
        favoriteCoverage,
    ] = await Promise.all([
        comedianIds.length === 0
            ? Promise.resolve([])
            : db.comedianFollowerObservation.findMany({
                  where: {
                      comedianId: { in: comedianIds },
                      observedAt: {
                          gte: windows.socialBaselineStart,
                          lt: windows.end,
                      },
                  },
                  select: {
                      comedianId: true,
                      platform: true,
                      followerCount: true,
                      observedAt: true,
                  },
              }),
        comedianUuids.length === 0
            ? Promise.resolve([])
            : db.favoriteComedian.findMany({
                  where: {
                      comedianId: { in: comedianUuids },
                      createdAt: {
                          gte: windows.baselineStart,
                          lt: windows.end,
                      },
                  },
                  select: { comedianId: true, createdAt: true },
              }),
        db.discoveryImpressionEvent.findMany({
            where: {
                entityType: SHOW_ENTITY_TYPE,
                entityId: { in: showIds },
                surface: DISCOVERY_SURFACE,
                impressedAt: {
                    gte: windows.baselineStart,
                    lt: windows.end,
                },
            },
            select: {
                entityId: true,
                profileId: true,
                anonymousVisitorId: true,
                impressedAt: true,
            },
        }),
        db.discoveryEngagementEvent.findMany({
            where: {
                engagementType: DETAIL_ENGAGEMENT_TYPE,
                engagedAt: {
                    gte: windows.baselineStart,
                    lt: windows.end,
                },
                impression: {
                    entityType: SHOW_ENTITY_TYPE,
                    entityId: { in: showIds },
                    surface: DISCOVERY_SURFACE,
                },
            },
            select: {
                engagedAt: true,
                impression: {
                    select: {
                        entityId: true,
                        profileId: true,
                        anonymousVisitorId: true,
                    },
                },
            },
        }),
        db.$queryRaw<TicketIntentRow[]>(Prisma.sql`
            SELECT
                t.show_id AS "showId",
                i.profile_id AS "profileId",
                i.anonymous_visitor_id AS "anonymousVisitorId",
                t.created_at AS "observedAt"
            FROM ticket_purchase_click_events t
            JOIN discovery_impression_events i
              ON i.event_id = t.discovery_impression_event_id
             AND i.entity_type = ${SHOW_ENTITY_TYPE}
             AND i.entity_id = t.show_id
             AND i.surface = ${DISCOVERY_SURFACE}
            WHERE t.show_id IN (${Prisma.join(showIds)})
              AND t.created_at >= ${windows.baselineStart}
              AND t.created_at < ${windows.end}
        `),
        db.discoveryImpressionEvent.aggregate({
            where: {
                entityType: SHOW_ENTITY_TYPE,
                surface: DISCOVERY_SURFACE,
            },
            _min: { impressedAt: true },
        }),
        db.favoriteComedian.aggregate({
            where: { createdAt: { not: null } },
            _min: { createdAt: true },
        }),
    ]);

    const followersByComedianId = new Map<
        number,
        DiscoveryFollowerObservation[]
    >();
    for (const follower of followers) {
        pushByShowId(followersByComedianId, follower.comedianId, {
            comedianId: follower.comedianId,
            platform: follower.platform,
            followerCount: follower.followerCount,
            observedAt: follower.observedAt,
        });
    }
    const favoritesByComedianUuid = new Map<string, Date[]>();
    for (const favorite of favorites) {
        if (favorite.createdAt) {
            const values =
                favoritesByComedianUuid.get(favorite.comedianId) ?? [];
            values.push(favorite.createdAt);
            favoritesByComedianUuid.set(favorite.comedianId, values);
        }
    }
    const impressionsByShowId = new Map<
        number,
        DiscoveryActivityObservation[]
    >();
    for (const impression of impressions) {
        pushByShowId(impressionsByShowId, impression.entityId, {
            actorKey: actorKey(
                impression.profileId,
                impression.anonymousVisitorId,
            ),
            observedAt: impression.impressedAt,
        });
    }
    const detailsByShowId = new Map<number, DiscoveryActivityObservation[]>();
    for (const detail of details) {
        pushByShowId(detailsByShowId, detail.impression.entityId, {
            actorKey: actorKey(
                detail.impression.profileId,
                detail.impression.anonymousVisitorId,
            ),
            observedAt: detail.engagedAt,
        });
    }
    const ticketIntentsByShowId = new Map<
        number,
        DiscoveryActivityObservation[]
    >();
    for (const intent of ticketIntents) {
        pushByShowId(ticketIntentsByShowId, intent.showId, {
            actorKey: actorKey(intent.profileId, intent.anonymousVisitorId),
            observedAt: intent.observedAt,
        });
    }

    return {
        stale,
        inputs: shows.map((show) => {
            const comedians = comediansByShowId.get(show.id) ?? [];
            return {
                showId: show.id,
                asOf,
                legacyPopularity: show.popularity,
                showDate: show.date,
                ticketsSoldOut: show.ticketsSoldOut,
                hasPurchasePath: show.tickets.some(({ purchaseUrl }) =>
                    Boolean(purchaseUrl?.trim()),
                ),
                followerObservations: comedians.flatMap(
                    ({ id }) => followersByComedianId.get(id) ?? [],
                ),
                favoriteCreatedAt: comedians.flatMap(
                    ({ uuid }) => favoritesByComedianUuid.get(uuid) ?? [],
                ),
                impressions: impressionsByShowId.get(show.id) ?? [],
                detailEngagements: detailsByShowId.get(show.id) ?? [],
                ticketIntents: ticketIntentsByShowId.get(show.id) ?? [],
                discoveryCoverageStart:
                    discoveryCoverage._min.impressedAt ?? undefined,
                favoriteCoverageStart:
                    favoriteCoverage._min.createdAt ?? undefined,
            };
        }),
    };
}

const productionDependencies: DiscoveryFeatureSnapshotJobDependencies = {
    loadBatch: loadDiscoveryFeatureInputBatch,
    persistSnapshot: async (snapshot) => {
        await db.$executeRaw(buildDiscoveryFeatureSnapshotUpsert(snapshot));
    },
};

function errorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}

export async function runDiscoveryFeatureSnapshotJob(
    options: DiscoveryFeatureSnapshotJobOptions = {},
    dependencies: DiscoveryFeatureSnapshotJobDependencies = productionDependencies,
): Promise<DiscoveryFeatureSnapshotJobResult> {
    const asOf = canonicalDiscoveryFeatureAsOf(options.asOf ?? new Date());
    const logger = options.logger ?? console;
    const batch = await dependencies.loadBatch({
        asOf,
        batchSize: normalizeBatchSize(options.batchSize),
    });
    const failures: DiscoveryFeatureSnapshotJobFailure[] = [];
    let succeeded = 0;

    for (
        let offset = 0;
        offset < batch.inputs.length;
        offset += PERSIST_CONCURRENCY
    ) {
        const chunk = batch.inputs.slice(offset, offset + PERSIST_CONCURRENCY);
        await Promise.all(
            chunk.map(async (input) => {
                try {
                    const snapshot = computeDiscoveryFeatures(input);
                    await dependencies.persistSnapshot(snapshot);
                    succeeded += 1;
                } catch (error) {
                    const message = errorMessage(error);
                    failures.push({ showId: input.showId, error: message });
                    logger.error(
                        `[discovery-feature-snapshots] show ${input.showId} failed: ${message}`,
                    );
                }
            }),
        );
    }

    const result: DiscoveryFeatureSnapshotJobResult = {
        asOf: asOf.toISOString(),
        processed: batch.inputs.length,
        succeeded,
        failed: failures.length,
        stale: Math.max(0, batch.stale - succeeded),
        failures: failures.sort((left, right) => left.showId - right.showId),
    };
    logger.info(
        `[discovery-feature-snapshots] processed=${result.processed} ` +
            `succeeded=${result.succeeded} failed=${result.failed} ` +
            `stale=${result.stale} asOf=${result.asOf}`,
    );
    return result;
}
