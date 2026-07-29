import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { buildComedianImageUrls } from "@/lib/data/comedian/imageAssets";
import { resolveNearbyZips } from "@/util/location/resolveNearbyZips";

type TrendingComedianRow = {
    id: number;
    uuid: string;
    name: string;
    instagram_account: string | null;
    instagram_followers: number | null;
    tiktok_account: string | null;
    tiktok_followers: number | null;
    youtube_account: string | null;
    youtube_followers: number | null;
    website: string | null;
    popularity: number;
    linktree: string | null;
    has_image: boolean;
    active_avatar_path: string | null;
    show_count: number;
};

type TrendingComedianOptions = {
    zipCode?: string;
    distanceMiles?: number;
};

type TrendingComediansQueryArgs = {
    now: Date;
    fetchLimit: number;
    fetchOffset: number;
    nearbyZips?: readonly string[] | null;
};

const MAX_COMEDIANS_LIMIT = 100;
// Fetch 4× the requested limit from DB (capped at 50) so the app-layer shuffle
// has enough variety without pulling an unbounded result set.
const POOL_MULTIPLIER = 4;
const MAX_POOL_SIZE = 50;
const MIN_UPCOMING_SHOWS = 3;
const MIN_POPULARITY = 0.4;

export function buildTrendingComediansQuery({
    now,
    fetchLimit,
    fetchOffset,
    nearbyZips,
}: TrendingComediansQueryArgs): Prisma.Sql {
    const hasZipScope = Boolean(nearbyZips?.length);
    const zipJoin = hasZipScope
        ? Prisma.sql`JOIN clubs cl ON cl.id = s.club_id`
        : Prisma.empty;
    const zipFilter = hasZipScope
        ? Prisma.sql`AND cl.zip_code IN (${Prisma.join(nearbyZips ?? [])})`
        : Prisma.empty;

    // Table/column mappings: comedians@@map, lineup_items@@map, shows@@map,
    // tagged_comedians@@map, tags@@map. Comedian.uuid=comedians.uuid,
    // LineupItem.comedianId=lineup_items.comedian_id, Comedian.parentComedianId=parent_comedian_id.
    return Prisma.sql`
        WITH eligible_lineups AS (
            SELECT
                CASE
                    WHEN performer.parent_comedian_id IS NULL THEN performer.id
                    ELSE performer.parent_comedian_id
                END AS canonical_comedian_id,
                COUNT(*)::int AS show_count
            FROM lineup_items li
            JOIN comedians performer ON performer.uuid = li.comedian_id
            JOIN shows s ON s.id = li.show_id
            ${zipJoin}
            WHERE s.date > ${now}
              ${zipFilter}
              AND (
                  performer.parent_comedian_id IS NULL
                  OR performer.visible = true
              )
            GROUP BY canonical_comedian_id
        ),
        comedian_counts AS (
            SELECT
                c.id,
                c.uuid,
                c.name,
                c.instagram_account,
                c.instagram_followers,
                c.tiktok_account,
                c.tiktok_followers,
                c.youtube_account,
                c.youtube_followers,
                c.website,
                c.popularity,
                c.linktree,
                c.has_image,
                image_asset.avatar_path AS active_avatar_path,
                el.show_count
            FROM comedians c
            JOIN eligible_lineups el ON el.canonical_comedian_id = c.id
            LEFT JOIN LATERAL (
                SELECT avatar_path
                FROM comedian_image_assets
                WHERE comedian_id = c.id
                  AND is_active = true
                  AND avatar_path IS NOT NULL
                ORDER BY published_at DESC, id DESC
                LIMIT 1
            ) image_asset ON true
            WHERE
                c.visible = true
                AND c.popularity > ${MIN_POPULARITY}
                AND c.parent_comedian_id IS NULL
                AND NOT EXISTS (
                    SELECT 1 FROM tagged_comedians tc
                    JOIN tags t ON t.id = tc.tag_id
                    WHERE tc.comedian_id = c.uuid
                        AND t.slug IN ('alias', 'non_human', 'non comic')
                )
                AND NOT EXISTS (
                    SELECT 1 FROM comedian_deny_list dl
                    WHERE dl.name = c.name
                )
        )
        SELECT *
        FROM comedian_counts
        WHERE show_count > ${MIN_UPCOMING_SHOWS}
        ORDER BY (has_image OR active_avatar_path IS NOT NULL) DESC, show_count DESC
        LIMIT ${fetchLimit}
        OFFSET ${fetchOffset}
    `;
}

export async function getTrendingComedians(
    limit = 8,
    offset = 0,
    options: TrendingComedianOptions = {},
): Promise<ComedianDTO[]> {
    const safeLimit = Math.min(Math.max(1, limit), MAX_COMEDIANS_LIMIT);
    const now = new Date();
    const nearbyZips =
        options.zipCode && /^\d{5}(-\d{4})?$/.test(options.zipCode)
            ? resolveNearbyZips(options.zipCode, options.distanceMiles)
            : null;

    const cteQuery = (fetchLimit: number, fetchOffset: number) =>
        db.$queryRaw<TrendingComedianRow[]>(
            buildTrendingComediansQuery({
                now,
                fetchLimit,
                fetchOffset,
                nearbyZips,
            }),
        );

    let selected: TrendingComedianRow[];
    try {
        if (offset === 0) {
            // For the first page, fetch a larger pool and shuffle to add variety.
            const poolSize = Math.min(
                safeLimit * POOL_MULTIPLIER,
                MAX_POOL_SIZE,
            );
            const rows = await cteQuery(poolSize, 0);
            // Shuffle in application code to avoid ORDER BY RANDOM() full sort at the DB layer.
            for (let i = rows.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [rows[i], rows[j]] = [rows[j], rows[i]];
            }
            selected = rows.slice(0, safeLimit);
        } else {
            // For paginated requests the shuffle is incompatible with stable paging,
            // so fetch exactly what the caller asked for at the given offset.
            selected = await cteQuery(safeLimit, offset);
        }
    } catch (err) {
        console.error("getTrendingComedians: query failed", err);
        return [];
    }

    return selected.map((row) => ({
        id: row.id,
        uuid: row.uuid,
        name: row.name,
        imageUrl: buildComedianImageUrls({
            name: row.name,
            hasImage: row.has_image,
            activeAsset: row.active_avatar_path
                ? { avatarPath: row.active_avatar_path }
                : null,
        }).imageUrl,
        hasImage: row.has_image || Boolean(row.active_avatar_path),
        socialData: {
            id: row.id,
            instagramAccount: row.instagram_account,
            instagramFollowers: row.instagram_followers,
            tiktokAccount: row.tiktok_account,
            tiktokFollowers: row.tiktok_followers,
            youtubeAccount: row.youtube_account,
            youtubeFollowers: row.youtube_followers,
            website: row.website,
            popularity: row.popularity,
            linktree: row.linktree,
        },
        showCount: Number(row.show_count),
    }));
}
