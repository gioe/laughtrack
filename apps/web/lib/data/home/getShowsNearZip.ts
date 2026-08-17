import { db } from "@/lib/db";
import { DISCOVERY_FEATURE_VERSION } from "@/lib/discovery/features";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { resolveNearbyZips } from "@/util/location/resolveNearbyZips";
import { Prisma } from "@prisma/client";
import {
    rankNearYouCandidates,
    rankNearYouCandidatesWithDiagnostics,
    type NearYouFeatureSnapshot,
} from "./discoveryRanker";
import { findShowsForHome } from "./findShowsForHome";
import {
    HOME_SHOW_RAIL_CANDIDATE_LIMIT,
    selectDiverseShowsByTime,
} from "./showRailSelection";
import {
    type DiscoveryAssignmentReason,
    type DiscoveryAvailabilityAtImpression,
    type DiscoveryShowImpressionContexts,
} from "@/lib/discovery/telemetry";

export interface NearYouCandidateOptions {
    actorKey: string;
    profileId?: string;
}

export interface NearYouTelemetryOptions {
    actorKey?: string | null;
    profileId?: string;
    experimentVariant: "control" | "candidate";
}

export interface NearYouShowsWithTelemetry {
    shows: ShowDTO[];
    impressionContexts: DiscoveryShowImpressionContexts;
}

type NearYouSnapshotRow = NearYouFeatureSnapshot & { showId: number };

async function findLatestSnapshots(
    showIds: readonly number[],
    now: Date,
): Promise<NearYouSnapshotRow[]> {
    return db.$queryRaw<NearYouSnapshotRow[]>(Prisma.sql`
        SELECT DISTINCT ON (show_id)
            show_id AS "showId",
            feature_version AS "featureVersion",
            as_of AS "asOf",
            prominence,
            momentum,
            growth,
            confidence,
            availability
        FROM discovery_show_feature_snapshots
        WHERE show_id IN (${Prisma.join(showIds)})
          AND feature_version = ${DISCOVERY_FEATURE_VERSION}
          AND as_of <= ${now}
        ORDER BY show_id ASC, as_of DESC, computed_at DESC, id DESC
    `);
}

export async function getShowsNearZip(
    zipCode: string,
    radius?: number,
    candidateOptions?: NearYouCandidateOptions,
): Promise<ShowDTO[]> {
    if (!zipCode || !/^\d{5}(-\d{4})?$/.test(zipCode)) return [];

    const now = new Date();
    const nearbyZips = resolveNearbyZips(zipCode, radius);
    const where = {
        date: { gte: now },
        club: { visible: true, zipCode: { in: nearbyZips } },
    };

    if (!candidateOptions) {
        const candidates = await findShowsForHome(
            where,
            [{ date: "asc" }, { id: "asc" }],
            HOME_SHOW_RAIL_CANDIDATE_LIMIT,
            {
                zipCode,
                sortByHomeRelevance: false,
                requireLineup: true,
            },
        );
        return selectDiverseShowsByTime(candidates);
    }

    const candidates = await findShowsForHome(
        where,
        [{ popularity: "desc" }, { date: "asc" }],
        50,
        {
            zipCode,
            profileId: candidateOptions.profileId,
            requireLineup: true,
        },
    );
    if (candidates.length === 0) return [];

    const snapshots = await findLatestSnapshots(
        candidates.map(({ id }) => id),
        now,
    );
    const snapshotByShowId = new Map(
        snapshots.map((snapshot) => [snapshot.showId, snapshot]),
    );

    const rankedCandidates = rankNearYouCandidates(
        candidates.map((show) => ({
            show,
            snapshot: snapshotByShowId.get(show.id),
            affinity: candidateOptions.profileId
                ? show.lineup?.some(({ isFavorite }) => isFavorite)
                    ? 1
                    : 0
                : 0.5,
        })),
        {
            now,
            maxDistanceMiles: radius ?? 25,
            actorKey: candidateOptions.actorKey,
            take: HOME_SHOW_RAIL_CANDIDATE_LIMIT,
        },
    );
    return selectDiverseShowsByTime(rankedCandidates);
}

function controlAvailability(show: ShowDTO): DiscoveryAvailabilityAtImpression {
    if (show.soldOut) return "unavailable";
    return show.tickets?.some(
        (ticket) => !ticket.soldOut && Boolean(ticket.purchaseUrl),
    )
        ? "available"
        : "unknown";
}

function assignmentReason(actorKey?: string | null): DiscoveryAssignmentReason {
    return actorKey ? "stable_actor_assignment" : "cookieless_bootstrap";
}

export async function getShowsNearZipWithTelemetry(
    zipCode: string,
    radius: number,
    options: NearYouTelemetryOptions,
): Promise<NearYouShowsWithTelemetry> {
    if (!zipCode || !/^\d{5}(-\d{4})?$/.test(zipCode)) {
        return { shows: [], impressionContexts: {} };
    }

    const now = new Date();
    const nearbyZips = resolveNearbyZips(zipCode, radius);
    const where = {
        date: { gte: now },
        club: { visible: true, zipCode: { in: nearbyZips } },
    };
    const reason = assignmentReason(options.actorKey);
    const baseContext = {
        assignmentEligible: Boolean(options.actorKey),
        assignmentReason: reason,
        maxDistanceMiles: radius,
    };

    if (options.experimentVariant === "control" || !options.actorKey) {
        const candidates = await findShowsForHome(
            where,
            [{ date: "asc" }, { id: "asc" }],
            HOME_SHOW_RAIL_CANDIDATE_LIMIT,
            {
                zipCode,
                sortByHomeRelevance: false,
                requireLineup: true,
            },
        );
        const shows = selectDiverseShowsByTime(candidates);
        return {
            shows,
            impressionContexts: Object.fromEntries(
                shows.map((show) => [
                    show.id,
                    {
                        ...baseContext,
                        explorationSelected: false,
                        distanceMiles: show.distanceMiles ?? null,
                        availabilityAtImpression: controlAvailability(show),
                        featureVersion: null,
                    },
                ]),
            ),
        };
    }

    const candidates = await findShowsForHome(
        where,
        [{ popularity: "desc" }, { date: "asc" }],
        50,
        {
            zipCode,
            profileId: options.profileId,
            requireLineup: true,
        },
    );
    if (candidates.length === 0) {
        return { shows: [], impressionContexts: {} };
    }
    const snapshots = await findLatestSnapshots(
        candidates.map(({ id }) => id),
        now,
    );
    const snapshotByShowId = new Map(
        snapshots.map((snapshot) => [snapshot.showId, snapshot]),
    );
    const ranked = rankNearYouCandidatesWithDiagnostics(
        candidates.map((show) => ({
            show,
            snapshot: snapshotByShowId.get(show.id),
            affinity: options.profileId
                ? show.lineup?.some(({ isFavorite }) => isFavorite)
                    ? 1
                    : 0
                : 0.5,
        })),
        {
            now,
            maxDistanceMiles: radius,
            actorKey: options.actorKey,
            take: HOME_SHOW_RAIL_CANDIDATE_LIMIT,
        },
    );

    const rankedByShowId = new Map(
        ranked.map((rankedShow) => [rankedShow.show.id, rankedShow]),
    );
    const selectedShows = selectDiverseShowsByTime(
        ranked.map(({ show }) => show),
    );
    const selectedRanked = selectedShows.flatMap((show) => {
        const rankedShow = rankedByShowId.get(show.id);
        return rankedShow ? [rankedShow] : [];
    });

    return {
        shows: selectedShows,
        impressionContexts: Object.fromEntries(
            selectedRanked.map(
                ({ show, snapshot, featureVersion, explorationSelected }) => [
                    show.id,
                    {
                        ...baseContext,
                        explorationSelected,
                        distanceMiles: show.distanceMiles ?? null,
                        availabilityAtImpression: snapshot.availability,
                        featureVersion,
                    },
                ],
            ),
        ),
    };
}
