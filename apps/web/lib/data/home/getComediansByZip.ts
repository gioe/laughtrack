import zipcodes from "zipcodes";
import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { buildComedianImageUrl } from "@/util/imageUtil";

type NearYouComedianRow = {
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
    show_count: number;
};

function resolveZipCodes(zipCode: string, radius?: number): string[] {
    if (!radius || radius < 1 || radius > 500) {
        return [zipCode];
    }
    try {
        const results = zipcodes.radius(zipCode, radius);
        if (!results || results.length === 0) return [zipCode];
        return results.map((z: string | zipcodes.ZipCode) =>
            typeof z === "string" ? z : z.zip,
        );
    } catch {
        return [zipCode];
    }
}

export async function getComediansByZip(
    zipCode: string,
    radius?: number,
): Promise<ComedianDTO[]> {
    if (!zipCode) return [];

    // Validate zip code format before querying to prevent unexpected behavior
    if (!/^\d{5}(-\d{4})?$/.test(zipCode)) return [];

    const now = new Date();
    const nearbyZips = resolveZipCodes(zipCode, radius);

    const rows = await db.$queryRaw<NearYouComedianRow[]>`
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
                c.has_image,
                COUNT(DISTINCT s.id)::int AS show_count
            FROM comedians c
            JOIN lineup_items li ON li.comedian_id = c.uuid
            JOIN shows s ON s.id = li.show_id
            JOIN clubs cl ON cl.id = s.club_id
            WHERE cl.zip_code IN (${Prisma.join(nearbyZips)})
              AND s.date > ${now}
              AND c.parent_comedian_id IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM tagged_comedians tc
                  JOIN tags t ON t.id = tc.tag_id
                  WHERE tc.comedian_id = c.uuid
                    AND t.slug IN ('alias', 'non_human', 'non comic')
              )
            GROUP BY c.id, c.uuid, c.name, c.instagram_account, c.instagram_followers,
                     c.tiktok_account, c.tiktok_followers, c.youtube_account,
                     c.youtube_followers, c.website, c.popularity, c.linktree, c.has_image
        )
        SELECT *
        FROM comedian_counts
        ORDER BY popularity DESC
        LIMIT 8
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
        show_count: Number(row.show_count),
    }));
}
