import { db } from "@/lib/db";

type NullableDate = Date | string | null;

type LatestRunRow = {
    id: bigint | number;
    exported_at: NullableDate;
    duration_seconds: number;
    shows_scraped: number;
    shows_saved: number;
    clubs_processed: number;
    clubs_successful: number;
    clubs_failed: number;
    errors_total: number;
    success_rate: number;
};

type FailureTrendRow = Pick<
    LatestRunRow,
    "id" | "exported_at" | "clubs_failed" | "errors_total" | "success_rate"
>;

type FailedClubRow = {
    club_id: number | null;
    club_name: string;
    error_message: string | null;
    http_status: number | null;
    bot_block_detected: boolean | null;
    execution_time_seconds: number;
};

type StaleScraperKeyRow = {
    scraper_key: string;
    enabled_source_count: bigint | number;
    recent_show_count: bigint | number;
    most_recent_scrape: NullableDate;
};

type SourceIssueRow = {
    club_id: number;
    club_name: string;
    platform: string;
    scraper_key: string | null;
    source_url: string | null;
    issue: string;
};

type ClubWithoutFutureShowsRow = {
    club_id: number;
    club_name: string;
    city: string | null;
    state: string | null;
    enabled_source_count: bigint | number;
    last_show_date: NullableDate;
};

type IncompleteShowRow = {
    show_id: number;
    show_name: string | null;
    show_date: NullableDate;
    club_id: number;
    club_name: string;
    missing_fields: string[];
};

type MissingMetadataRow = {
    club_id: number;
    club_name: string;
    city: string | null;
    state: string | null;
    missing_fields: string[];
};

type PendingReviewRow = {
    queue: string;
    count: bigint | number;
    oldest_created_at: NullableDate;
};

export type AdminOverviewRun = {
    id: number;
    exportedAt: string;
    durationSeconds: number;
    showsScraped: number;
    showsSaved: number;
    clubsProcessed: number;
    clubsSuccessful: number;
    clubsFailed: number;
    errorsTotal: number;
    successRate: number;
};

export type AdminOverviewFailureTrend = {
    id: number;
    exportedAt: string;
    clubsFailed: number;
    errorsTotal: number;
    successRate: number;
};

export type AdminOverviewData = {
    latestRun: AdminOverviewRun | null;
    recentFailureTrend: AdminOverviewFailureTrend[];
    latestFailedClubs: Array<{
        clubId: number | null;
        clubName: string;
        errorMessage: string | null;
        httpStatus: number | null;
        botBlockDetected: boolean;
        executionTimeSeconds: number;
    }>;
    outliers: {
        staleScraperKeys: Array<{
            scraperKey: string;
            enabledSourceCount: number;
            recentShowCount: number;
            mostRecentScrape: string | null;
        }>;
        sourceIssues: Array<{
            clubId: number;
            clubName: string;
            platform: string;
            scraperKey: string | null;
            sourceUrl: string | null;
            issue: string;
        }>;
        clubsWithoutFutureShows: Array<{
            clubId: number;
            clubName: string;
            city: string | null;
            state: string | null;
            enabledSourceCount: number;
            lastShowDate: string | null;
        }>;
        incompleteShows: Array<{
            showId: number;
            showName: string | null;
            showDate: string | null;
            clubId: number;
            clubName: string;
            missingFields: string[];
        }>;
        missingMetadata: Array<{
            clubId: number;
            clubName: string;
            city: string | null;
            state: string | null;
            missingFields: string[];
        }>;
        pendingReviews: Array<{
            queue: string;
            count: number;
            oldestCreatedAt: string | null;
        }>;
    };
};

function toNumber(value: bigint | number | null | undefined): number {
    if (typeof value === "bigint") return Number(value);
    return Number(value ?? 0);
}

function toIso(value: NullableDate): string | null {
    if (!value) return null;
    return value instanceof Date
        ? value.toISOString()
        : new Date(value).toISOString();
}

function mapLatestRun(row: LatestRunRow): AdminOverviewRun {
    return {
        id: toNumber(row.id),
        exportedAt: toIso(row.exported_at) ?? "",
        durationSeconds: row.duration_seconds,
        showsScraped: row.shows_scraped,
        showsSaved: row.shows_saved,
        clubsProcessed: row.clubs_processed,
        clubsSuccessful: row.clubs_successful,
        clubsFailed: row.clubs_failed,
        errorsTotal: row.errors_total,
        successRate: row.success_rate,
    };
}

export async function getAdminOverviewData(): Promise<AdminOverviewData> {
    const [
        latestRunRows,
        recentFailureRows,
        latestFailedClubRows,
        staleScraperKeyRows,
        sourceIssueRows,
        clubsWithoutFutureShowRows,
        incompleteShowRows,
        missingMetadataRows,
        pendingReviewRows,
    ] = await Promise.all([
        db.$queryRaw<LatestRunRow[]>`
            SELECT id, exported_at, duration_seconds, shows_scraped, shows_saved,
                   clubs_processed, clubs_successful, clubs_failed, errors_total,
                   success_rate
            FROM scraper_runs
            ORDER BY exported_at DESC
            LIMIT 1
        `,
        db.$queryRaw<FailureTrendRow[]>`
            SELECT id, exported_at, clubs_failed, errors_total, success_rate
            FROM scraper_runs
            ORDER BY exported_at DESC
            LIMIT 8
        `,
        db.$queryRaw<FailedClubRow[]>`
            WITH latest_run AS (
                SELECT id
                FROM scraper_runs
                ORDER BY exported_at DESC
                LIMIT 1
            )
            SELECT src.club_id, src.club_name, src.error_message, src.http_status,
                   src.bot_block_detected, src.execution_time_seconds
            FROM scraper_run_clubs src
            JOIN latest_run lr ON lr.id = src.run_id
            WHERE src.success = FALSE
            ORDER BY src.bot_block_detected DESC, src.execution_time_seconds DESC, src.club_name ASC
            LIMIT 10
        `,
        db.$queryRaw<StaleScraperKeyRow[]>`
            WITH enabled_keys AS (
                SELECT ss.scraper_key, COUNT(DISTINCT ss.club_id) AS enabled_source_count
                FROM scraping_sources ss
                WHERE ss.enabled = TRUE
                  AND ss.scraper_key IS NOT NULL
                  AND ss.scraper_key <> ''
                GROUP BY ss.scraper_key
            ),
            recent_activity AS (
                SELECT s.last_scraped_by AS scraper_key,
                       COUNT(*) AS recent_show_count,
                       MAX(s.last_scraped_date) AS most_recent_scrape
                FROM shows s
                WHERE s.last_scraped_by IS NOT NULL
                  AND s.last_scraped_date IS NOT NULL
                  AND s.last_scraped_date >= NOW() - INTERVAL '7 days'
                GROUP BY s.last_scraped_by
            )
            SELECT ek.scraper_key, ek.enabled_source_count,
                   COALESCE(ra.recent_show_count, 0) AS recent_show_count,
                   ra.most_recent_scrape
            FROM enabled_keys ek
            LEFT JOIN recent_activity ra ON ra.scraper_key = ek.scraper_key
            WHERE ra.scraper_key IS NULL
            ORDER BY ek.enabled_source_count DESC, ek.scraper_key ASC
            LIMIT 8
        `,
        db.$queryRaw<SourceIssueRow[]>`
            SELECT c.id AS club_id, c.name AS club_name, ss.platform::text AS platform,
                   ss.scraper_key, ss.source_url,
                   CASE
                       WHEN ss.scraper_key IS NULL OR BTRIM(ss.scraper_key) = '' THEN 'missing scraper key'
                       WHEN ss.source_url IS NULL OR BTRIM(ss.source_url) = '' THEN 'missing source locator'
                       ELSE 'configuration needs review'
                   END AS issue
            FROM scraping_sources ss
            JOIN clubs c ON c.id = ss.club_id
            WHERE ss.enabled = TRUE
              AND (
                  ss.scraper_key IS NULL OR BTRIM(ss.scraper_key) = ''
                  OR (
                      (ss.source_url IS NULL OR BTRIM(ss.source_url) = '')
                      AND ss.seatengine_id IS NULL
                      AND (ss.eventbrite_id IS NULL OR BTRIM(ss.eventbrite_id) = '')
                      AND (ss.ticketmaster_id IS NULL OR BTRIM(ss.ticketmaster_id) = '')
                      AND (ss.wix_event_id IS NULL OR BTRIM(ss.wix_event_id) = '')
                      AND (ss.ovationtix_id IS NULL OR BTRIM(ss.ovationtix_id) = '')
                      AND (ss.squadup_id IS NULL OR BTRIM(ss.squadup_id) = '')
                      AND (ss.seatengine_v3_id IS NULL OR BTRIM(ss.seatengine_v3_id) = '')
                  )
              )
            ORDER BY c.name ASC, ss.priority ASC
            LIMIT 8
        `,
        db.$queryRaw<ClubWithoutFutureShowsRow[]>`
            SELECT c.id AS club_id, c.name AS club_name, c.city, c.state,
                   COUNT(DISTINCT ss.id) AS enabled_source_count,
                   MAX(s.date) AS last_show_date
            FROM clubs c
            JOIN scraping_sources ss ON ss.club_id = c.id AND ss.enabled = TRUE
            LEFT JOIN shows s ON s.club_id = c.id
            WHERE COALESCE(c.visible, TRUE) = TRUE
              AND c.status = 'active'
            GROUP BY c.id, c.name, c.city, c.state
            HAVING COUNT(s.id) FILTER (WHERE s.date > NOW()) = 0
            ORDER BY enabled_source_count DESC, last_show_date ASC NULLS FIRST, c.name ASC
            LIMIT 8
        `,
        db.$queryRaw<IncompleteShowRow[]>`
            SELECT s.id AS show_id, s.name AS show_name, s.date AS show_date,
                   c.id AS club_id, c.name AS club_name,
                   ARRAY_REMOVE(ARRAY[
                       CASE WHEN s.name IS NULL OR BTRIM(s.name) = '' THEN 'title' END,
                       CASE WHEN s.description IS NULL OR BTRIM(s.description) = '' THEN 'description' END,
                       CASE WHEN s.show_page_url IS NULL OR BTRIM(s.show_page_url) = '' THEN 'show URL' END,
                       CASE WHEN NOT EXISTS (SELECT 1 FROM tickets t WHERE t.show_id = s.id) THEN 'tickets' END,
                       CASE WHEN NOT EXISTS (SELECT 1 FROM lineup_items li WHERE li.show_id = s.id) THEN 'lineup' END
                   ], NULL) AS missing_fields
            FROM shows s
            JOIN clubs c ON c.id = s.club_id
            WHERE s.date > NOW()
              AND (
                  s.name IS NULL OR BTRIM(s.name) = ''
                  OR s.description IS NULL OR BTRIM(s.description) = ''
                  OR s.show_page_url IS NULL OR BTRIM(s.show_page_url) = ''
                  OR NOT EXISTS (SELECT 1 FROM tickets t WHERE t.show_id = s.id)
                  OR NOT EXISTS (SELECT 1 FROM lineup_items li WHERE li.show_id = s.id)
              )
            ORDER BY s.date ASC
            LIMIT 8
        `,
        db.$queryRaw<MissingMetadataRow[]>`
            SELECT c.id AS club_id, c.name AS club_name, c.city, c.state,
                   ARRAY_REMOVE(ARRAY[
                       CASE WHEN c.description IS NULL OR BTRIM(c.description) = '' THEN 'description' END,
                       CASE WHEN c.hours IS NULL THEN 'hours' END,
                       CASE WHEN c.timezone IS NULL OR BTRIM(c.timezone) = '' THEN 'timezone' END,
                       CASE WHEN c.phone_number IS NULL OR BTRIM(c.phone_number) = '' THEN 'phone' END,
                       CASE WHEN c.has_image = FALSE THEN 'image' END
                   ], NULL) AS missing_fields
            FROM clubs c
            WHERE COALESCE(c.visible, TRUE) = TRUE
              AND c.status = 'active'
              AND (
                  c.description IS NULL OR BTRIM(c.description) = ''
                  OR c.hours IS NULL
                  OR c.timezone IS NULL OR BTRIM(c.timezone) = ''
                  OR c.phone_number IS NULL OR BTRIM(c.phone_number) = ''
                  OR c.has_image = FALSE
              )
            ORDER BY CARDINALITY(ARRAY_REMOVE(ARRAY[
                       CASE WHEN c.description IS NULL OR BTRIM(c.description) = '' THEN 'description' END,
                       CASE WHEN c.hours IS NULL THEN 'hours' END,
                       CASE WHEN c.timezone IS NULL OR BTRIM(c.timezone) = '' THEN 'timezone' END,
                       CASE WHEN c.phone_number IS NULL OR BTRIM(c.phone_number) = '' THEN 'phone' END,
                       CASE WHEN c.has_image = FALSE THEN 'image' END
                   ], NULL)) DESC, c.name ASC
            LIMIT 8
        `,
        db.$queryRaw<PendingReviewRow[]>`
            SELECT queue, count, oldest_created_at
            FROM (
                SELECT 'Podcast candidates' AS queue, COUNT(*) AS count, MIN(created_at) AS oldest_created_at
                FROM podcast_candidate_reviews
                WHERE candidate_status = 'pending'
                UNION ALL
                SELECT 'Podcast appearances' AS queue, COUNT(*) AS count, MIN(created_at) AS oldest_created_at
                FROM comedian_podcasts
                WHERE review_status = 'pending'
                UNION ALL
                SELECT 'Episode appearances' AS queue, COUNT(*) AS count, MIN(created_at) AS oldest_created_at
                FROM episode_appearance_reviews
                WHERE candidate_status = 'pending'
            ) review_queues
            WHERE count > 0
            ORDER BY count DESC, oldest_created_at ASC NULLS LAST
        `,
    ]);

    return {
        latestRun: latestRunRows[0] ? mapLatestRun(latestRunRows[0]) : null,
        recentFailureTrend: recentFailureRows.map((row) => ({
            id: toNumber(row.id),
            exportedAt: toIso(row.exported_at) ?? "",
            clubsFailed: row.clubs_failed,
            errorsTotal: row.errors_total,
            successRate: row.success_rate,
        })),
        latestFailedClubs: latestFailedClubRows.map((row) => ({
            clubId: row.club_id,
            clubName: row.club_name,
            errorMessage: row.error_message,
            httpStatus: row.http_status,
            botBlockDetected: Boolean(row.bot_block_detected),
            executionTimeSeconds: row.execution_time_seconds,
        })),
        outliers: {
            staleScraperKeys: staleScraperKeyRows.map((row) => ({
                scraperKey: row.scraper_key,
                enabledSourceCount: toNumber(row.enabled_source_count),
                recentShowCount: toNumber(row.recent_show_count),
                mostRecentScrape: toIso(row.most_recent_scrape),
            })),
            sourceIssues: sourceIssueRows.map((row) => ({
                clubId: row.club_id,
                clubName: row.club_name,
                platform: row.platform,
                scraperKey: row.scraper_key,
                sourceUrl: row.source_url,
                issue: row.issue,
            })),
            clubsWithoutFutureShows: clubsWithoutFutureShowRows.map((row) => ({
                clubId: row.club_id,
                clubName: row.club_name,
                city: row.city,
                state: row.state,
                enabledSourceCount: toNumber(row.enabled_source_count),
                lastShowDate: toIso(row.last_show_date),
            })),
            incompleteShows: incompleteShowRows.map((row) => ({
                showId: row.show_id,
                showName: row.show_name,
                showDate: toIso(row.show_date),
                clubId: row.club_id,
                clubName: row.club_name,
                missingFields: row.missing_fields,
            })),
            missingMetadata: missingMetadataRows.map((row) => ({
                clubId: row.club_id,
                clubName: row.club_name,
                city: row.city,
                state: row.state,
                missingFields: row.missing_fields,
            })),
            pendingReviews: pendingReviewRows.map((row) => ({
                queue: row.queue,
                count: toNumber(row.count),
                oldestCreatedAt: toIso(row.oldest_created_at),
            })),
        },
    };
}
