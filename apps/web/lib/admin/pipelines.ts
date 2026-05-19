import { db } from "@/lib/db";

type NullableDate = Date | string | null;

type PipelineRunRow = {
    id: bigint | number;
    run_key: string;
    pipeline_key: string;
    exported_at: NullableDate;
    duration_seconds: number;
    shows_scraped: number;
    shows_saved: number;
    shows_inserted: number;
    shows_updated: number;
    shows_failed_save: number;
    shows_skipped_dedup: number;
    shows_validation_failed: number;
    shows_db_errors: number;
    clubs_processed: number;
    clubs_successful: number;
    clubs_failed: number;
    errors_total: number;
    success_rate: number;
};

type PipelineAggregateRow = {
    pipeline_key: string;
    run_count: bigint | number;
    average_duration_seconds: number | null;
    average_success_rate: number | null;
    total_shows_saved: bigint | number;
    total_errors: bigint | number;
    latest_exported_at: NullableDate;
};

type PipelineClubRow = {
    club_id: number | null;
    club_name: string;
    num_shows: number;
    execution_time_seconds: number;
    success: boolean;
    error_message: string | null;
    shows_saved: number | null;
    errors_count: number | null;
    http_status: number | null;
    bot_block_detected: boolean | null;
    playwright_fallback_used: boolean | null;
};

type PipelineErrorRow = {
    club_name: string;
    error_message: string | null;
    execution_time_seconds: number;
};

export type AdminPipelineRun = {
    id: number;
    runKey: string;
    pipelineKey: string;
    pipelineName: string;
    status: "healthy" | "degraded" | "failing";
    exportedAt: string;
    durationSeconds: number;
    showsScraped: number;
    showsSaved: number;
    showsInserted: number;
    showsUpdated: number;
    showsFailedSave: number;
    showsSkippedDedup: number;
    showsValidationFailed: number;
    showsDbErrors: number;
    clubsProcessed: number;
    clubsSuccessful: number;
    clubsFailed: number;
    errorsTotal: number;
    successRate: number;
};

export type AdminPipelineSummary = {
    pipelineKey: string;
    pipelineName: string;
    runCount: number;
    averageDurationSeconds: number;
    averageSuccessRate: number;
    totalShowsSaved: number;
    totalErrors: number;
    latestExportedAt: string | null;
    latestRun: AdminPipelineRun | null;
};

export type AdminPipelineClubStat = {
    clubId: number | null;
    clubName: string;
    numShows: number;
    executionTimeSeconds: number;
    success: boolean;
    errorMessage: string | null;
    showsSaved: number | null;
    errorsCount: number | null;
    httpStatus: number | null;
    botBlockDetected: boolean;
    playwrightFallbackUsed: boolean;
};

export type AdminPipelinesData = {
    summaries: AdminPipelineSummary[];
    recentRuns: AdminPipelineRun[];
    latestSlowClubs: AdminPipelineClubStat[];
    latestFailedClubs: AdminPipelineClubStat[];
    latestErrors: Array<{
        clubName: string;
        errorMessage: string | null;
        executionTimeSeconds: number;
    }>;
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

function pipelineName(key: string): string {
    if (key === "scraper") return "Venue scraper";
    return key
        .split(/[-_\s]+/)
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

function runStatus(row: PipelineRunRow): AdminPipelineRun["status"] {
    if (row.errors_total > 0 || row.clubs_failed > 0 || row.success_rate < 95) {
        return row.success_rate < 75 ? "failing" : "degraded";
    }
    return "healthy";
}

function mapRun(row: PipelineRunRow): AdminPipelineRun {
    return {
        id: toNumber(row.id),
        runKey: row.run_key,
        pipelineKey: row.pipeline_key,
        pipelineName: pipelineName(row.pipeline_key),
        status: runStatus(row),
        exportedAt: toIso(row.exported_at) ?? "",
        durationSeconds: row.duration_seconds,
        showsScraped: row.shows_scraped,
        showsSaved: row.shows_saved,
        showsInserted: row.shows_inserted,
        showsUpdated: row.shows_updated,
        showsFailedSave: row.shows_failed_save,
        showsSkippedDedup: row.shows_skipped_dedup,
        showsValidationFailed: row.shows_validation_failed,
        showsDbErrors: row.shows_db_errors,
        clubsProcessed: row.clubs_processed,
        clubsSuccessful: row.clubs_successful,
        clubsFailed: row.clubs_failed,
        errorsTotal: row.errors_total,
        successRate: row.success_rate,
    };
}

function mapClub(row: PipelineClubRow): AdminPipelineClubStat {
    return {
        clubId: row.club_id,
        clubName: row.club_name,
        numShows: row.num_shows,
        executionTimeSeconds: row.execution_time_seconds,
        success: row.success,
        errorMessage: row.error_message,
        showsSaved: row.shows_saved,
        errorsCount: row.errors_count,
        httpStatus: row.http_status,
        botBlockDetected: Boolean(row.bot_block_detected),
        playwrightFallbackUsed: Boolean(row.playwright_fallback_used),
    };
}

export async function listAdminPipelines(): Promise<AdminPipelinesData> {
    const [
        latestRunRows,
        aggregateRows,
        recentRunRows,
        slowClubRows,
        failedClubRows,
        errorRows,
    ] = await Promise.all([
        db.$queryRaw<PipelineRunRow[]>`
            WITH normalized AS (
                SELECT sr.*, SPLIT_PART(sr.run_key, ':', 1) AS pipeline_key
                FROM scraper_runs sr
            )
            SELECT DISTINCT ON (pipeline_key)
                   id, run_key, pipeline_key, exported_at, duration_seconds,
                   shows_scraped, shows_saved, shows_inserted, shows_updated,
                   shows_failed_save, shows_skipped_dedup,
                   shows_validation_failed, shows_db_errors,
                   clubs_processed, clubs_successful, clubs_failed,
                   errors_total, success_rate
            FROM normalized
            ORDER BY pipeline_key ASC, exported_at DESC
        `,
        db.$queryRaw<PipelineAggregateRow[]>`
            WITH normalized AS (
                SELECT sr.*, SPLIT_PART(sr.run_key, ':', 1) AS pipeline_key
                FROM scraper_runs sr
            ),
            ranked AS (
                SELECT normalized.*,
                       ROW_NUMBER() OVER (
                           PARTITION BY pipeline_key
                           ORDER BY exported_at DESC
                       ) AS recency_rank
                FROM normalized
            )
            SELECT pipeline_key,
                   COUNT(*) AS run_count,
                   AVG(duration_seconds) AS average_duration_seconds,
                   AVG(success_rate) AS average_success_rate,
                   COALESCE(SUM(shows_saved), 0) AS total_shows_saved,
                   COALESCE(SUM(errors_total), 0) AS total_errors,
                   MAX(exported_at) AS latest_exported_at
            FROM ranked
            WHERE recency_rank <= 20
            GROUP BY pipeline_key
            ORDER BY latest_exported_at DESC
        `,
        db.$queryRaw<PipelineRunRow[]>`
            SELECT id, run_key, SPLIT_PART(run_key, ':', 1) AS pipeline_key,
                   exported_at, duration_seconds, shows_scraped, shows_saved,
                   shows_inserted, shows_updated, shows_failed_save,
                   shows_skipped_dedup, shows_validation_failed,
                   shows_db_errors, clubs_processed, clubs_successful,
                   clubs_failed, errors_total, success_rate
            FROM scraper_runs
            ORDER BY exported_at DESC
            LIMIT 12
        `,
        db.$queryRaw<PipelineClubRow[]>`
            WITH latest_run AS (
                SELECT id
                FROM scraper_runs
                ORDER BY exported_at DESC
                LIMIT 1
            )
            SELECT src.club_id, src.club_name, src.num_shows,
                   src.execution_time_seconds, src.success, src.error_message,
                   src.shows_saved, src.errors_count, src.http_status,
                   src.bot_block_detected, src.playwright_fallback_used
            FROM scraper_run_clubs src
            JOIN latest_run lr ON lr.id = src.run_id
            ORDER BY src.execution_time_seconds DESC, src.club_name ASC
            LIMIT 8
        `,
        db.$queryRaw<PipelineClubRow[]>`
            WITH latest_run AS (
                SELECT id
                FROM scraper_runs
                ORDER BY exported_at DESC
                LIMIT 1
            )
            SELECT src.club_id, src.club_name, src.num_shows,
                   src.execution_time_seconds, src.success, src.error_message,
                   src.shows_saved, src.errors_count, src.http_status,
                   src.bot_block_detected, src.playwright_fallback_used
            FROM scraper_run_clubs src
            JOIN latest_run lr ON lr.id = src.run_id
            WHERE src.success = FALSE OR src.error_message IS NOT NULL
            ORDER BY src.bot_block_detected DESC,
                     src.execution_time_seconds DESC,
                     src.club_name ASC
            LIMIT 8
        `,
        db.$queryRaw<PipelineErrorRow[]>`
            WITH latest_run AS (
                SELECT id
                FROM scraper_runs
                ORDER BY exported_at DESC
                LIMIT 1
            )
            SELECT sre.club_name, sre.error_message, sre.execution_time_seconds
            FROM scraper_run_errors sre
            JOIN latest_run lr ON lr.id = sre.run_id
            ORDER BY sre.execution_time_seconds DESC, sre.club_name ASC
            LIMIT 8
        `,
    ]);

    const latestRuns = latestRunRows.map(mapRun);

    return {
        summaries: aggregateRows.map((row) => ({
            pipelineKey: row.pipeline_key,
            pipelineName: pipelineName(row.pipeline_key),
            runCount: toNumber(row.run_count),
            averageDurationSeconds: row.average_duration_seconds ?? 0,
            averageSuccessRate: row.average_success_rate ?? 0,
            totalShowsSaved: toNumber(row.total_shows_saved),
            totalErrors: toNumber(row.total_errors),
            latestExportedAt: toIso(row.latest_exported_at),
            latestRun:
                latestRuns.find(
                    (run) => run.pipelineKey === row.pipeline_key,
                ) ?? null,
        })),
        recentRuns: recentRunRows.map(mapRun),
        latestSlowClubs: slowClubRows.map(mapClub),
        latestFailedClubs: failedClubRows.map(mapClub),
        latestErrors: errorRows.map((row) => ({
            clubName: row.club_name,
            errorMessage: row.error_message,
            executionTimeSeconds: row.execution_time_seconds,
        })),
    };
}
