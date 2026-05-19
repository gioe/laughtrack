import {
    Activity,
    AlertTriangle,
    Clock3,
    DatabaseZap,
    Gauge,
    Workflow,
} from "lucide-react";
import Link from "next/link";
import { listAdminPipelines } from "@/lib/admin/pipelines";
import type {
    AdminPipelineClubStat,
    AdminPipelineRun,
} from "@/lib/admin/pipelines";

export const dynamic = "force-dynamic";

function formatDateTime(value: string | null): string {
    if (!value) return "Not recorded";
    return new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
    }).format(new Date(value));
}

function formatSeconds(value: number): string {
    if (value < 60) return `${value.toFixed(1)}s`;
    return `${Math.floor(value / 60)}m ${Math.round(value % 60)}s`;
}

function formatPercent(value: number): string {
    return `${value.toFixed(1)}%`;
}

function statusClass(status: AdminPipelineRun["status"]): string {
    if (status === "healthy") {
        return "border-green-700/30 bg-green-50 text-green-900";
    }
    if (status === "degraded") {
        return "border-amber-700/30 bg-amber-50 text-amber-900";
    }
    return "border-red-700/30 bg-red-50 text-red-900";
}

function Metric({
    label,
    value,
    icon: Icon,
}: {
    label: string;
    value: string;
    icon: typeof Activity;
}) {
    return (
        <div className="rounded-md border border-copper/20 bg-white p-4">
            <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-md bg-copper/10 text-copper-dark">
                    <Icon className="h-5 w-5" />
                </span>
                <div>
                    <p className="font-dmSans text-caption font-semibold uppercase text-soft-charcoal">
                        {label}
                    </p>
                    <p className="font-gilroy-bold text-h3 text-cedar">
                        {value}
                    </p>
                </div>
            </div>
        </div>
    );
}

function ClubLink({ club }: { club: AdminPipelineClubStat }) {
    if (!club.clubId) return <span>{club.clubName}</span>;
    return (
        <Link
            href={`/admin/clubs/${club.clubId}`}
            className="font-semibold text-copper-dark hover:underline"
        >
            {club.clubName}
        </Link>
    );
}

export default async function AdminPipelinesPage() {
    const data = await listAdminPipelines();
    const latestRun = data.recentRuns[0] ?? null;

    return (
        <div className="space-y-6">
            <div>
                <p className="font-dmSans text-caption font-semibold uppercase text-copper-dark">
                    Admin · Pipelines
                </p>
                <h1 className="mt-1 font-chivo text-h1 text-cedar">
                    Pipeline status
                </h1>
                <p className="mt-2 max-w-3xl font-dmSans text-body text-soft-charcoal">
                    Run health, throughput, failures, and slow spots from the
                    operational pipelines that persist performance summaries.
                </p>
            </div>

            <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                <Metric
                    label="Pipelines"
                    value={data.summaries.length.toLocaleString()}
                    icon={Workflow}
                />
                <Metric
                    label="Latest success"
                    value={
                        latestRun ? formatPercent(latestRun.successRate) : "N/A"
                    }
                    icon={Gauge}
                />
                <Metric
                    label="Latest duration"
                    value={
                        latestRun
                            ? formatSeconds(latestRun.durationSeconds)
                            : "N/A"
                    }
                    icon={Clock3}
                />
                <Metric
                    label="Latest saved"
                    value={(latestRun?.showsSaved ?? 0).toLocaleString()}
                    icon={DatabaseZap}
                />
                <Metric
                    label="Latest errors"
                    value={(latestRun?.errorsTotal ?? 0).toLocaleString()}
                    icon={AlertTriangle}
                />
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
                {data.summaries.length === 0 ? (
                    <div className="rounded-md border border-copper/20 bg-white p-4 font-dmSans text-body text-soft-charcoal lg:col-span-2">
                        No pipeline run summaries have been recorded yet.
                    </div>
                ) : (
                    data.summaries.map((summary) => (
                        <article
                            key={summary.pipelineKey}
                            className="rounded-md border border-copper/20 bg-white p-4"
                        >
                            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                                <div>
                                    <h2 className="font-gilroy-bold text-h3 text-cedar">
                                        {summary.pipelineName}
                                    </h2>
                                    <p className="font-dmSans text-caption text-soft-charcoal">
                                        {summary.runCount.toLocaleString()}{" "}
                                        recent runs · latest{" "}
                                        {formatDateTime(
                                            summary.latestExportedAt,
                                        )}
                                    </p>
                                </div>
                                {summary.latestRun && (
                                    <span
                                        className={`rounded-full border px-2 py-1 font-dmSans text-caption font-semibold ${statusClass(summary.latestRun.status)}`}
                                    >
                                        {summary.latestRun.status}
                                    </span>
                                )}
                            </div>
                            <dl className="grid gap-3 font-dmSans text-body text-soft-charcoal sm:grid-cols-2">
                                <div>
                                    <dt className="font-semibold text-cedar">
                                        Avg duration
                                    </dt>
                                    <dd>
                                        {formatSeconds(
                                            summary.averageDurationSeconds,
                                        )}
                                    </dd>
                                </div>
                                <div>
                                    <dt className="font-semibold text-cedar">
                                        Avg success
                                    </dt>
                                    <dd>
                                        {formatPercent(
                                            summary.averageSuccessRate,
                                        )}
                                    </dd>
                                </div>
                                <div>
                                    <dt className="font-semibold text-cedar">
                                        Shows saved
                                    </dt>
                                    <dd>
                                        {summary.totalShowsSaved.toLocaleString()}
                                    </dd>
                                </div>
                                <div>
                                    <dt className="font-semibold text-cedar">
                                        Errors
                                    </dt>
                                    <dd>
                                        {summary.totalErrors.toLocaleString()}
                                    </dd>
                                </div>
                            </dl>
                        </article>
                    ))
                )}
            </section>

            <section className="overflow-hidden rounded-md border border-copper/20 bg-white">
                <div className="border-b border-copper/15 bg-cedar px-4 py-3">
                    <h2 className="font-gilroy-bold text-h3 text-coconut-cream">
                        Recent runs
                    </h2>
                </div>
                {data.recentRuns.length === 0 ? (
                    <p className="p-4 font-dmSans text-body text-soft-charcoal">
                        No recent runs found.
                    </p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[920px] text-left font-dmSans text-body">
                            <thead className="bg-ecru-white text-caption uppercase text-soft-charcoal">
                                <tr>
                                    <th className="px-4 py-3">Pipeline</th>
                                    <th className="px-4 py-3">Status</th>
                                    <th className="px-4 py-3">Exported</th>
                                    <th className="px-4 py-3">Duration</th>
                                    <th className="px-4 py-3">Clubs</th>
                                    <th className="px-4 py-3">Shows</th>
                                    <th className="px-4 py-3">Saved</th>
                                    <th className="px-4 py-3">Errors</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-copper/15">
                                {data.recentRuns.map((run) => (
                                    <tr key={run.id}>
                                        <td className="px-4 py-3 font-semibold text-cedar">
                                            {run.pipelineName}
                                        </td>
                                        <td className="px-4 py-3">
                                            <span
                                                className={`rounded-full border px-2 py-1 text-caption font-semibold ${statusClass(run.status)}`}
                                            >
                                                {run.status}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-soft-charcoal">
                                            {formatDateTime(run.exportedAt)}
                                        </td>
                                        <td className="px-4 py-3 text-soft-charcoal">
                                            {formatSeconds(run.durationSeconds)}
                                        </td>
                                        <td className="px-4 py-3 text-soft-charcoal">
                                            {run.clubsSuccessful}/
                                            {run.clubsProcessed} ok
                                        </td>
                                        <td className="px-4 py-3 text-soft-charcoal">
                                            {run.showsScraped.toLocaleString()}
                                        </td>
                                        <td className="px-4 py-3 text-soft-charcoal">
                                            {run.showsSaved.toLocaleString()}{" "}
                                            saved ·{" "}
                                            {run.showsInserted.toLocaleString()}{" "}
                                            new ·{" "}
                                            {run.showsUpdated.toLocaleString()}{" "}
                                            updated
                                        </td>
                                        <td className="px-4 py-3 text-soft-charcoal">
                                            {run.errorsTotal.toLocaleString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-md border border-copper/20 bg-white">
                    <div className="border-b border-copper/15 px-4 py-3">
                        <h2 className="font-gilroy-bold text-h3 text-cedar">
                            Slowest latest-run clubs
                        </h2>
                    </div>
                    <div className="divide-y divide-copper/15">
                        {data.latestSlowClubs.length === 0 ? (
                            <p className="p-4 font-dmSans text-body text-soft-charcoal">
                                No club timing rows found.
                            </p>
                        ) : (
                            data.latestSlowClubs.map((club) => (
                                <div
                                    key={`${club.clubId ?? club.clubName}-slow`}
                                    className="px-4 py-3 font-dmSans text-body"
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <ClubLink club={club} />
                                            <p className="text-caption text-soft-charcoal">
                                                {club.numShows} shows ·{" "}
                                                {club.showsSaved ?? 0} saved
                                                {club.playwrightFallbackUsed
                                                    ? " · browser fallback"
                                                    : ""}
                                            </p>
                                        </div>
                                        <span className="font-semibold text-cedar">
                                            {formatSeconds(
                                                club.executionTimeSeconds,
                                            )}
                                        </span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                <div className="rounded-md border border-copper/20 bg-white">
                    <div className="border-b border-copper/15 px-4 py-3">
                        <h2 className="font-gilroy-bold text-h3 text-cedar">
                            Latest failures
                        </h2>
                    </div>
                    <div className="divide-y divide-copper/15">
                        {data.latestFailedClubs.length === 0 &&
                        data.latestErrors.length === 0 ? (
                            <p className="p-4 font-dmSans text-body text-soft-charcoal">
                                No failures in the latest run.
                            </p>
                        ) : (
                            data.latestFailedClubs.map((club) => (
                                <div
                                    key={`${club.clubId ?? club.clubName}-failed`}
                                    className="px-4 py-3 font-dmSans text-body"
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <ClubLink club={club} />
                                            <p className="mt-1 text-caption text-soft-charcoal">
                                                {club.errorMessage ??
                                                    "No error message captured"}
                                            </p>
                                        </div>
                                        {club.botBlockDetected && (
                                            <span className="rounded-md border border-amber-700/30 bg-amber-50 px-2 py-1 text-caption font-semibold text-amber-900">
                                                Bot block
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                        {data.latestErrors.map((error) => (
                            <div
                                key={`${error.clubName}-${error.errorMessage}`}
                                className="px-4 py-3 font-dmSans text-body"
                            >
                                <p className="font-semibold text-cedar">
                                    {error.clubName}
                                </p>
                                <p className="mt-1 text-caption text-soft-charcoal">
                                    {error.errorMessage ??
                                        "No error message captured"}{" "}
                                    ·{" "}
                                    {formatSeconds(error.executionTimeSeconds)}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>
        </div>
    );
}
