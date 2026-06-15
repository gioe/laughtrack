import { Prisma } from "@prisma/client";

type PodcastDenyListWriter = Pick<Prisma.TransactionClient, "$queryRaw">;

type DeniedPodcastRow = {
    podcast_id: number;
    title: string;
    source: string;
    source_podcast_id: string;
    feed_url: string | null;
};

export type DeniedPodcastSummary = {
    podcastId: number;
    title: string;
    source: string;
    sourcePodcastId: string;
    feedUrl: string | null;
};

function serializeDeniedPodcast(row: DeniedPodcastRow): DeniedPodcastSummary {
    return {
        podcastId: row.podcast_id,
        title: row.title,
        source: row.source,
        sourcePodcastId: row.source_podcast_id,
        feedUrl: row.feed_url,
    };
}

export async function denyPodcastsHostedByComedianName(
    tx: PodcastDenyListWriter,
    {
        comedianName,
        reason,
        deniedBy,
    }: {
        comedianName: string;
        reason: string;
        deniedBy: string | null;
    },
): Promise<DeniedPodcastSummary[]> {
    const normalizedName = comedianName.trim().replace(/\s+/g, " ");
    if (!normalizedName) return [];

    const rows = await tx.$queryRaw<DeniedPodcastRow[]>`
        WITH targets AS (
            SELECT DISTINCT
                p.id AS podcast_id,
                p.title,
                p.source,
                p.source_podcast_id,
                p.feed_url
            FROM comedian_podcasts cp
            JOIN comedians c ON c.id = cp.comedian_id
            JOIN podcasts p ON p.id = cp.podcast_id
            WHERE cp.review_status = 'accepted'
              AND cp.association_type IN ('host', 'cohost')
              AND lower(btrim(regexp_replace(replace(c.name, chr(160), ' '), '[[:space:]]+', ' ', 'g'))) =
                  lower(btrim(regexp_replace(replace(${normalizedName}, chr(160), ' '), '[[:space:]]+', ' ', 'g')))
        ),
        updated AS (
            UPDATE podcast_deny_list dl
            SET source = t.source,
                source_podcast_id = t.source_podcast_id,
                feed_url = t.feed_url,
                reason = ${reason},
                denied_at = NOW(),
                denied_by = ${deniedBy},
                restored_at = NULL,
                restored_by = NULL,
                updated_at = NOW()
            FROM targets t
            WHERE dl.podcast_id = t.podcast_id
               OR (dl.source = t.source AND dl.source_podcast_id = t.source_podcast_id)
               OR (t.feed_url IS NOT NULL AND dl.feed_url = t.feed_url)
            RETURNING
                t.podcast_id,
                t.title,
                t.source,
                t.source_podcast_id,
                t.feed_url
        ),
        inserted AS (
            INSERT INTO podcast_deny_list (
                podcast_id,
                source,
                source_podcast_id,
                feed_url,
                reason,
                denied_by
            )
            SELECT
                t.podcast_id,
                t.source,
                t.source_podcast_id,
                t.feed_url,
                ${reason},
                ${deniedBy}
            FROM targets t
            WHERE NOT EXISTS (
                SELECT 1
                FROM updated u
                WHERE u.podcast_id = t.podcast_id
            )
            ON CONFLICT (podcast_id) DO UPDATE
            SET source = EXCLUDED.source,
                source_podcast_id = EXCLUDED.source_podcast_id,
                feed_url = EXCLUDED.feed_url,
                reason = EXCLUDED.reason,
                denied_at = NOW(),
                denied_by = EXCLUDED.denied_by,
                restored_at = NULL,
                restored_by = NULL,
                updated_at = NOW()
            RETURNING
                podcast_id
        )
        SELECT DISTINCT podcast_id, title, source, source_podcast_id, feed_url
        FROM updated
        UNION
        SELECT DISTINCT t.podcast_id, t.title, t.source, t.source_podcast_id, t.feed_url
        FROM inserted i
        JOIN targets t ON t.podcast_id = i.podcast_id
        ORDER BY title ASC, podcast_id ASC
    `;

    return rows.map(serializeDeniedPodcast);
}
