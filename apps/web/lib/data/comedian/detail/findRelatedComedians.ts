import { db } from "@/lib/db";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { buildComedianImageUrl } from "@/util/imageUtil";

const RELATED_LIMIT = 8;
const MIN_CO_APPEARANCES = 2;

type RelatedComedianRow = {
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
    co_appearances: number;
    upcoming_show_count: number;
};

export async function findRelatedComedians(
    comedianUuid: string,
): Promise<ComedianDTO[]> {
    if (!comedianUuid) return [];
    const now = new Date();

    try {
        const rows = await db.$queryRaw<RelatedComedianRow[]>`
            WITH target_shows AS (
                SELECT DISTINCT show_id
                FROM lineup_items
                WHERE comedian_id = ${comedianUuid}
            )
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
                COUNT(DISTINCT li.show_id)::int AS co_appearances,
                (
                    SELECT COUNT(*)::int
                    FROM lineup_items li2
                    JOIN shows s ON s.id = li2.show_id
                    WHERE li2.comedian_id = c.uuid AND s.date > ${now}
                ) AS upcoming_show_count
            FROM lineup_items li
            JOIN comedians c ON c.uuid = li.comedian_id
            WHERE li.show_id IN (SELECT show_id FROM target_shows)
                AND li.comedian_id != ${comedianUuid}
                AND c.parent_comedian_id IS NULL
                AND NOT EXISTS (
                    SELECT 1 FROM tagged_comedians tc
                    JOIN tags t ON t.id = tc.tag_id
                    WHERE tc.comedian_id = c.uuid
                        AND t.slug IN ('alias', 'non_human', 'non comic')
                )
            GROUP BY c.id, c.uuid, c.name, c.instagram_account,
                c.instagram_followers, c.tiktok_account, c.tiktok_followers,
                c.youtube_account, c.youtube_followers, c.website, c.popularity,
                c.linktree, c.has_image
            HAVING COUNT(DISTINCT li.show_id) >= ${MIN_CO_APPEARANCES}
            ORDER BY co_appearances DESC, c.popularity DESC, c.name ASC
            LIMIT ${RELATED_LIMIT}
        `;

        return rows.map((row) => ({
            id: row.id,
            uuid: row.uuid,
            name: row.name,
            imageUrl: buildComedianImageUrl(row.name, row.has_image),
            hasImage: Boolean(row.has_image),
            social_data: {
                id: row.id,
                instagram_account: row.instagram_account,
                instagram_followers: row.instagram_followers,
                tiktok_account: row.tiktok_account,
                tiktok_followers: row.tiktok_followers,
                youtube_account: row.youtube_account,
                youtube_followers: row.youtube_followers,
                website: row.website,
                popularity: row.popularity,
                linktree: row.linktree,
            },
            show_count: Number(row.upcoming_show_count),
            co_appearances: Number(row.co_appearances),
        }));
    } catch (err) {
        console.error("findRelatedComedians: query failed", err);
        return [];
    }
}
