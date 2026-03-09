import { db } from "@/lib/db";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { buildComedianImageUrl } from "@/util/imageUtil";

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
    show_count: number;
};

const MAX_COMEDIANS_LIMIT = 100;
// Fetch 4× the requested limit from DB (capped at 50) so the app-layer shuffle
// has enough variety without pulling an unbounded result set.
const POOL_MULTIPLIER = 4;
const MAX_POOL_SIZE = 50;

export async function getTrendingComedians(
    limit = 8,
    offset = 0,
): Promise<ComedianDTO[]> {
    const safeLimit = Math.min(Math.max(1, limit), MAX_COMEDIANS_LIMIT);
    const now = new Date();

    // Table/column mappings: comedians@@map, lineup_items@@map, shows@@map,
    // tagged_comedians@@map, tags@@map. Comedian.uuid=comedians.uuid,
    // LineupItem.comedianId=lineup_items.comedian_id, Comedian.parentComedianId=parent_comedian_id
    const cteQuery = (fetchLimit: number, fetchOffset: number) => db.$queryRaw<
        TrendingComedianRow[]
    >`
        WITH comedian_counts AS (
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
                (
                    (
                        SELECT COUNT(*)
                        FROM lineup_items li
                        JOIN shows s ON s.id = li.show_id
                        WHERE li.comedian_id = c.uuid AND s.date > ${now}
                    ) + COALESCE((
                        SELECT SUM(cnt) FROM (
                            SELECT COUNT(*) AS cnt
                            FROM comedians alt
                            JOIN lineup_items li ON li.comedian_id = alt.uuid
                            JOIN shows s ON s.id = li.show_id
                            WHERE alt.parent_comedian_id = c.id AND s.date > ${now}
                        ) t
                    ), 0)
                )::int AS show_count
            FROM comedians c
            WHERE
                c.parent_comedian_id IS NULL
                AND NOT EXISTS (
                    SELECT 1 FROM tagged_comedians tc
                    JOIN tags t ON t.id = tc.tag_id
                    WHERE tc.comedian_id = c.uuid
                        AND t.slug IN ('alias', 'non_human', 'non comic')
                )
                AND (
                    EXISTS (
                        SELECT 1 FROM lineup_items li
                        JOIN shows s ON s.id = li.show_id
                        WHERE li.comedian_id = c.uuid AND s.date > ${now}
                    ) OR EXISTS (
                        SELECT 1 FROM comedians alt
                        JOIN lineup_items li ON li.comedian_id = alt.uuid
                        JOIN shows s ON s.id = li.show_id
                        WHERE alt.parent_comedian_id = c.id AND s.date > ${now}
                    )
                )
        )
        SELECT *
        FROM comedian_counts
        WHERE show_count > 3
        ORDER BY show_count DESC
        LIMIT ${fetchLimit}
        OFFSET ${fetchOffset}
    `;

    let selected: TrendingComedianRow[];
    if (offset === 0) {
        // For the first page, fetch a larger pool and shuffle to add variety.
        const poolSize = Math.min(safeLimit * POOL_MULTIPLIER, MAX_POOL_SIZE);
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

    return selected.map((row) => ({
        id: row.id,
        uuid: row.uuid,
        name: row.name,
        imageUrl: buildComedianImageUrl(row.name),
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
        show_count: Number(row.show_count),
    }));
}
