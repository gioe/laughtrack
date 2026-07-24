import { db } from "@/lib/db";
import { DISCOVERY_FEATURE_VERSION } from "@/lib/discovery/features";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { resolveNearbyZips } from "@/util/location/resolveNearbyZips";
import { Prisma } from "@prisma/client";
import {
    rankNearYouCandidates,
    type NearYouFeatureSnapshot,
} from "./discoveryRanker";
import { findShowsForHome } from "./findShowsForHome";

export interface NearYouCandidateOptions {
    actorKey: string;
    profileId?: string;
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

    const snapshots = await findLatestSnapshots(
        candidates.map(({ id }) => id),
        now,
    );
    const snapshotByShowId = new Map(
        snapshots.map((snapshot) => [snapshot.showId, snapshot]),
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
