import { Prisma } from "@prisma/client";
import { format, fromZonedTime, toZonedTime } from "date-fns-tz";
import { db } from "@/lib/db";
import { buildComedianImageUrls } from "@/lib/data/comedian/imageAssets";
import { buildShowSelect, mapShowRowToDTO } from "@/lib/data/show/showSelect";
import type { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import type { ShowDTO } from "@/objects/class/show/show.interface";
import { DEFAULT_SHOW_TIMEZONE } from "@/util/dateUtil";

const MIN_LINEUP_BEARING_SHOWS = 10;
const MIN_FREQUENT_PERFORMERS = 3;
const FREQUENT_PERFORMER_LIMIT = 8;

type FrequentPerformerRow = {
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

export type ClubHighlights = {
    tonightShows: ShowDTO[];
    nextShow: ShowDTO | null;
    frequentPerformers: ComedianDTO[];
};

export type FindClubHighlightsOptions = {
    now?: Date;
};

export function buildFrequentPerformersQuery(
    clubId: number,
    since: Date,
    until: Date,
): Prisma.Sql {
    return Prisma.sql`
        WITH lineup_shows AS (
            SELECT DISTINCT s.id
            FROM shows s
            JOIN lineup_items li ON li.show_id = s.id
            WHERE s.club_id = ${clubId}
              AND s.date >= ${since}
              AND s.date <= ${until}
        ),
        canonical_appearances AS (
            SELECT DISTINCT
                COALESCE(performer.parent_comedian_id, performer.id)
                    AS canonical_comedian_id,
                li.show_id
            FROM lineup_items li
            JOIN lineup_shows ls ON ls.id = li.show_id
            JOIN comedians performer ON performer.uuid = li.comedian_id
            WHERE performer.visible = true
        ),
        coverage AS (
            SELECT COUNT(*)::int AS lineup_show_count
            FROM lineup_shows
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
            image_asset.avatar_path AS active_avatar_path,
            COUNT(DISTINCT ca.show_id)::int AS show_count
        FROM canonical_appearances ca
        JOIN comedians c ON c.id = ca.canonical_comedian_id
        CROSS JOIN coverage
        LEFT JOIN LATERAL (
            SELECT avatar_path
            FROM comedian_image_assets
            WHERE comedian_id = c.id
              AND is_active = true
              AND avatar_path IS NOT NULL
            ORDER BY published_at DESC, id DESC
            LIMIT 1
        ) image_asset ON true
        WHERE coverage.lineup_show_count >= ${MIN_LINEUP_BEARING_SHOWS}
          AND c.visible = true
          AND c.parent_comedian_id IS NULL
          AND NOT EXISTS (
              SELECT 1
              FROM tagged_comedians tc
              JOIN tags t ON t.id = tc.tag_id
              WHERE tc.comedian_id = c.uuid
                AND t.user_facing = false
          )
          AND NOT EXISTS (
              SELECT 1
              FROM comedian_deny_list dl
              WHERE dl.name = c.name
          )
        GROUP BY
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
            image_asset.avatar_path
        ORDER BY show_count DESC, c.popularity DESC, c.name ASC
        LIMIT ${FREQUENT_PERFORMER_LIMIT}
    `;
}

function twelveMonthsBefore(date: Date): Date {
    const result = new Date(date);
    result.setUTCFullYear(result.getUTCFullYear() - 1);
    return result;
}

function mapFrequentPerformer(row: FrequentPerformerRow): ComedianDTO {
    return {
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
    };
}

export async function findClubHighlights(
    clubId: number,
    options: FindClubHighlightsOptions = {},
): Promise<ClubHighlights | null> {
    const club = await db.club.findUnique({
        where: { id: clubId, status: "active" },
        select: { timezone: true },
    });
    if (!club) return null;

    const now = options.now ?? new Date();
    const timezone = club.timezone || DEFAULT_SHOW_TIMEZONE;
    const localDate = format(toZonedTime(now, timezone), "yyyy-MM-dd");
    const startOfTonight = fromZonedTime(`${localDate}T00:00:00`, timezone);
    const endOfTonight = fromZonedTime(`${localDate}T23:59:59.999`, timezone);
    const showSelect = buildShowSelect();

    const [tonightRows, nextRow, performerRows] = await Promise.all([
        db.show.findMany({
            where: {
                clubId,
                date: { gte: startOfTonight, lte: endOfTonight },
            },
            select: showSelect,
            orderBy: { date: "asc" },
        }),
        db.show.findFirst({
            where: {
                clubId,
                date: { gt: endOfTonight },
            },
            select: showSelect,
            orderBy: { date: "asc" },
        }),
        db.$queryRaw<FrequentPerformerRow[]>(
            buildFrequentPerformersQuery(clubId, twelveMonthsBefore(now), now),
        ),
    ]);

    const frequentPerformers =
        performerRows.length >= MIN_FREQUENT_PERFORMERS
            ? performerRows.map(mapFrequentPerformer)
            : [];

    return {
        tonightShows: tonightRows.map((show) => mapShowRowToDTO(show)),
        nextShow: nextRow ? mapShowRowToDTO(nextRow) : null,
        frequentPerformers,
    };
}
