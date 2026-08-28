import { db } from "@/lib/db";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { resolveNearbyZips } from "@/util/location/resolveNearbyZips";
import { Prisma } from "@prisma/client";
import { findShowsForHome } from "./findShowsForHome";
import {
    HOME_SHOW_RAIL_CANDIDATE_LIMIT,
    selectDiverseShowsByTime,
} from "./showRailSelection";

interface FavoriteComedianMemberRow {
    member_uuid: string;
}

async function findFavoriteComedianMemberUuids(
    profileId: string,
): Promise<string[]> {
    const rows = await db.$queryRaw<FavoriteComedianMemberRow[]>(Prisma.sql`
        WITH RECURSIVE favorite_ancestors AS (
            SELECT
                seed.id AS favorite_id,
                seed.id AS comedian_id,
                seed.parent_comedian_id
            FROM favorite_comedians favorite
            JOIN comedians seed ON seed.uuid = favorite.comedian_id
            WHERE favorite.profile_id = ${profileId}
              AND seed.visible = true

            UNION

            SELECT
                ancestors.favorite_id,
                parent.id AS comedian_id,
                parent.parent_comedian_id
            FROM favorite_ancestors ancestors
            JOIN comedians parent ON parent.id = ancestors.parent_comedian_id
        ),
        favorite_roots AS (
            SELECT DISTINCT root.id AS root_id
            FROM favorite_ancestors ancestors
            JOIN comedians root ON root.id = ancestors.comedian_id
            WHERE ancestors.parent_comedian_id IS NULL
              AND root.visible = true
        ),
        favorite_comedian_members AS (
            SELECT
                roots.root_id,
                root.id AS member_id,
                root.uuid AS member_uuid
            FROM favorite_roots roots
            JOIN comedians root ON root.id = roots.root_id

            UNION

            SELECT
                members.root_id,
                child.id AS member_id,
                child.uuid AS member_uuid
            FROM favorite_comedian_members members
            JOIN comedians child ON child.parent_comedian_id = members.member_id
        )
        SELECT DISTINCT member_uuid
        FROM favorite_comedian_members
        ORDER BY member_uuid
    `);

    return rows.map(({ member_uuid }) => member_uuid);
}

export async function getFavoriteComedianShows(
    profileId?: string | null,
    zipCode?: string | null,
    radius?: number,
): Promise<ShowDTO[]> {
    if (!profileId) {
        return [];
    }

    const usableZipCode =
        zipCode && /^\d{5}(-\d{4})?$/.test(zipCode) ? zipCode : null;
    const nearbyZips = usableZipCode
        ? resolveNearbyZips(usableZipCode, radius)
        : null;
    const favoriteComedianMemberUuids =
        await findFavoriteComedianMemberUuids(profileId);

    if (favoriteComedianMemberUuids.length === 0) {
        return [];
    }

    const candidates = await findShowsForHome(
        {
            date: { gte: new Date() },
            club: {
                visible: true,
                ...(nearbyZips ? { zipCode: { in: nearbyZips } } : {}),
            },
            lineupItems: {
                some: {
                    comedianId: { in: favoriteComedianMemberUuids },
                },
            },
        },
        [{ date: "asc" }, { id: "asc" }],
        HOME_SHOW_RAIL_CANDIDATE_LIMIT,
        usableZipCode
            ? {
                  profileId,
                  zipCode: usableZipCode,
                  sortByHomeRelevance: false,
                  requireLineup: true,
              }
            : {
                  profileId,
                  sortByHomeRelevance: false,
                  requireLineup: true,
              },
    );

    return selectDiverseShowsByTime(candidates);
}
