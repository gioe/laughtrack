import { db } from "@/lib/db";
import { DISCOVERY_FEATURE_VERSION } from "@/lib/discovery/features";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { resolveNearbyZips } from "@/util/location/resolveNearbyZips";
import {
    rankNearYouCandidates,
    type NearYouFeatureSnapshot,
} from "./discoveryRanker";
import { findShowsForHome } from "./findShowsForHome";

export interface NearYouCandidateOptions {
    actorKey: string;
    profileId?: string;
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
        return findShowsForHome(
            where,
            [{ popularity: "desc" }, { date: "asc" }],
            8,
            { zipCode, sortByHomeRelevance: true },
        );
    }

    const candidates = await findShowsForHome(
        where,
        [{ popularity: "desc" }, { date: "asc" }],
        50,
        {
            zipCode,
            profileId: candidateOptions.profileId,
        },
    );
    if (candidates.length === 0) return [];

    const snapshots = await db.discoveryShowFeatureSnapshot.findMany({
        where: {
            showId: { in: candidates.map(({ id }) => id) },
            featureVersion: DISCOVERY_FEATURE_VERSION,
            asOf: { lte: now },
        },
        select: {
            showId: true,
            featureVersion: true,
            asOf: true,
            prominence: true,
            momentum: true,
            growth: true,
            confidence: true,
            availability: true,
        },
        // PostgreSQL DISTINCT ON requires the distinct key first. The
        // remaining fields make "latest snapshot" deterministic.
        orderBy: [
            { showId: "asc" },
            { asOf: "desc" },
            { computedAt: "desc" },
            { id: "desc" },
        ],
        distinct: ["showId"],
    });
    const snapshotByShowId = new Map(
        snapshots.map((snapshot) => [
            snapshot.showId,
            snapshot as NearYouFeatureSnapshot,
        ]),
    );

    return rankNearYouCandidates(
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
            take: 8,
        },
    );
}
