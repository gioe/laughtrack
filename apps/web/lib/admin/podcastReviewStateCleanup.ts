export type PodcastReviewStateCleanupCandidate = {
    podcastId: number;
    title: string;
    source: string;
    sourcePodcastId: string;
    feedUrl: string | null;
};

type Queryable = {
    $queryRaw<T = unknown>(
        query: TemplateStringsArray,
        ...values: unknown[]
    ): Promise<T>;
};

type Executable = {
    $executeRaw(
        query: TemplateStringsArray,
        ...values: unknown[]
    ): Promise<number>;
};

const NO_HOST_REJECTION_REASON = "No accepted visible host after review";

export async function listPodcastReviewStateCleanupCandidates(
    db: Queryable,
): Promise<PodcastReviewStateCleanupCandidate[]> {
    return db.$queryRaw<PodcastReviewStateCleanupCandidate[]>`
        SELECT DISTINCT
            p.id AS "podcastId",
            p.title,
            p.source,
            p.source_podcast_id AS "sourcePodcastId",
            p.feed_url AS "feedUrl"
        FROM podcasts p
        WHERE EXISTS (
            SELECT 1
            FROM podcast_candidate_reviews pcr
            WHERE pcr.podcast_id = p.id
              AND pcr.candidate_status <> 'pending'
        )
          AND NOT EXISTS (
            SELECT 1
            FROM podcast_candidate_reviews pending
            WHERE pending.podcast_id = p.id
              AND pending.candidate_status = 'pending'
          )
          AND NOT EXISTS (
            SELECT 1
            FROM comedian_podcasts cp
            JOIN comedians comedian ON comedian.id = cp.comedian_id
            WHERE cp.podcast_id = p.id
              AND cp.review_status = 'accepted'
              AND cp.association_type IN ('host', 'cohost')
              AND comedian.visible = TRUE
          )
          AND NOT EXISTS (
            SELECT 1
            FROM podcast_deny_list pdl
            WHERE pdl.restored_at IS NULL
              AND (
                pdl.podcast_id = p.id
                OR (pdl.source = p.source AND pdl.source_podcast_id = p.source_podcast_id)
                OR (p.feed_url IS NOT NULL AND pdl.feed_url = p.feed_url)
              )
          )
        ORDER BY p.title ASC, p.id ASC
    `;
}

export async function applyPodcastReviewStateCleanup(
    db: Executable,
    {
        deniedBy,
        now = new Date(),
    }: {
        deniedBy: string;
        now?: Date;
    },
) {
    const deniedPodcastCount = await db.$executeRaw`
        INSERT INTO podcast_deny_list (
            podcast_id,
            source,
            source_podcast_id,
            feed_url,
            reason,
            denied_at,
            denied_by,
            restored_at,
            restored_by,
            created_at,
            updated_at
        )
        SELECT DISTINCT
            p.id,
            p.source,
            p.source_podcast_id,
            p.feed_url,
            ${NO_HOST_REJECTION_REASON},
            CAST(${now} AS timestamptz),
            ${deniedBy},
            NULL::timestamptz,
            NULL,
            CAST(${now} AS timestamptz),
            CAST(${now} AS timestamptz)
        FROM podcasts p
        WHERE EXISTS (
            SELECT 1
            FROM podcast_candidate_reviews pcr
            WHERE pcr.podcast_id = p.id
              AND pcr.candidate_status <> 'pending'
        )
          AND NOT EXISTS (
            SELECT 1
            FROM podcast_candidate_reviews pending
            WHERE pending.podcast_id = p.id
              AND pending.candidate_status = 'pending'
          )
          AND NOT EXISTS (
            SELECT 1
            FROM comedian_podcasts cp
            JOIN comedians comedian ON comedian.id = cp.comedian_id
            WHERE cp.podcast_id = p.id
              AND cp.review_status = 'accepted'
              AND cp.association_type IN ('host', 'cohost')
              AND comedian.visible = TRUE
          )
          AND NOT EXISTS (
            SELECT 1
            FROM podcast_deny_list pdl
            WHERE pdl.restored_at IS NULL
              AND (
                pdl.podcast_id = p.id
                OR (pdl.source = p.source AND pdl.source_podcast_id = p.source_podcast_id)
                OR (p.feed_url IS NOT NULL AND pdl.feed_url = p.feed_url)
              )
          )
        ON CONFLICT (podcast_id) DO UPDATE SET
            source = EXCLUDED.source,
            source_podcast_id = EXCLUDED.source_podcast_id,
            feed_url = EXCLUDED.feed_url,
            reason = EXCLUDED.reason,
            denied_at = EXCLUDED.denied_at,
            denied_by = EXCLUDED.denied_by,
            restored_at = NULL,
            restored_by = NULL,
            updated_at = EXCLUDED.updated_at
    `;

    const normalizedIgnoredReviewCount = await db.$executeRaw`
        UPDATE podcast_candidate_reviews
        SET candidate_status = 'rejected',
            reviewed_at = CAST(${now} AS timestamptz),
            reviewed_by = ${deniedBy},
            updated_at = CAST(${now} AS timestamptz)
        WHERE candidate_status = 'ignored'
    `;

    return {
        deniedPodcastCount,
        normalizedIgnoredReviewCount,
    };
}
