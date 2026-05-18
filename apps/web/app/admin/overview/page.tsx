import {
    AlertTriangle,
    ArrowUpRight,
    BadgeCheck,
    Bot,
    CalendarX2,
    CircleHelp,
    ClipboardList,
    Clock3,
    DatabaseZap,
    FileWarning,
    ListChecks,
    RadioTower,
} from "lucide-react";
import Link from "next/link";
import { getAdminOverviewData } from "@/lib/admin/overview";

export const dynamic = "force-dynamic";

function formatDateTime(value: string | null): string {
    if (!value) return "Not recorded";
    return new Intl.DateTimeFormat("en-US", {
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

function EmptyQueue() {
    return (
        <p className="font-dmSans text-caption text-soft-charcoal">
            No urgent outliers in this queue.
        </p>
    );
}

function QueueShell({
    title,
    count,
    icon: Icon,
    children,
}: {
    title: string;
    count: number;
    icon: typeof AlertTriangle;
    children: React.ReactNode;
}) {
    return (
        <section className="rounded-lg border border-copper/15 bg-white p-4 shadow-sm">
            <div className="mb-4 flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-copper/10 text-copper">
                        <Icon className="h-5 w-5" />
                    </div>
                    <h2 className="font-gilroy-bold text-body text-cedar">
                        {title}
                    </h2>
                </div>
                <span className="rounded-md bg-ecru-white px-2 py-1 font-dmSans text-caption font-semibold text-copper">
                    {count}
                </span>
            </div>
            {children}
        </section>
    );
}

function ClubLink({
    clubId,
    children,
}: {
    clubId: number | null;
    children: React.ReactNode;
}) {
    if (!clubId) {
        return <span>{children}</span>;
    }

    return (
        <Link
            href={`/admin/clubs/${clubId}`}
            className="inline-flex items-center gap-1 font-semibold text-copper hover:underline"
        >
            {children}
            <ArrowUpRight className="h-3.5 w-3.5" />
        </Link>
    );
}

export default async function AdminOverviewPage() {
    const data = await getAdminOverviewData();
    const latestRun = data.latestRun;
    const outliers = data.outliers;

    return (
        <div className="space-y-8">
            <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
                <div className="space-y-4">
                    <p className="font-dmSans text-caption font-semibold uppercase text-copper">
                        Overview
                    </p>
                    <h1 className="font-chivo text-h1 leading-tight text-cedar">
                        Scraper health with the queues that need a human next.
                    </h1>
                    <p className="max-w-3xl font-dmSans text-lead text-soft-charcoal">
                        Run summaries and data-quality checks are pulled live
                        from Postgres so the admin view tracks the same catalog
                        state the scraper writes.
                    </p>
                </div>
                <div className="rounded-lg border border-copper/20 bg-coconut-cream p-5 shadow-sm">
                    <div className="mb-3 flex items-center gap-3">
                        <DatabaseZap className="h-5 w-5 text-copper" />
                        <h2 className="font-gilroy-bold text-h3 text-cedar">
                            Scraper health
                        </h2>
                    </div>
                    {latestRun ? (
                        <div className="grid gap-3 sm:grid-cols-2">
                            <Metric
                                label="Success rate"
                                value={formatPercent(latestRun.successRate)}
                            />
                            <Metric
                                label="Saved shows"
                                value={latestRun.showsSaved.toLocaleString()}
                            />
                            <Metric
                                label="Failed clubs"
                                value={latestRun.clubsFailed.toLocaleString()}
                            />
                            <Metric
                                label="Run time"
                                value={formatSeconds(latestRun.durationSeconds)}
                            />
                            <p className="sm:col-span-2 font-dmSans text-caption text-soft-charcoal">
                                Latest run exported{" "}
                                {formatDateTime(latestRun.exportedAt)}
                            </p>
                        </div>
                    ) : (
                        <p className="font-dmSans text-body text-soft-charcoal">
                            No scraper run summaries have landed yet.
                        </p>
                    )}
                </div>
            </section>

            <section className="grid gap-4 md:grid-cols-4">
                <MetricBand
                    label="Runs trended"
                    value={data.recentFailureTrend.length.toLocaleString()}
                    icon={RadioTower}
                />
                <MetricBand
                    label="Clubs processed"
                    value={(latestRun?.clubsProcessed ?? 0).toLocaleString()}
                    icon={BadgeCheck}
                />
                <MetricBand
                    label="Run errors"
                    value={(latestRun?.errorsTotal ?? 0).toLocaleString()}
                    icon={AlertTriangle}
                />
                <MetricBand
                    label="Shows scraped"
                    value={(latestRun?.showsScraped ?? 0).toLocaleString()}
                    icon={ListChecks}
                />
            </section>

            <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
                <div className="rounded-lg border border-copper/15 bg-white p-5 shadow-sm">
                    <div className="mb-4 flex items-center gap-3">
                        <Clock3 className="h-5 w-5 text-copper" />
                        <h2 className="font-gilroy-bold text-h3 text-cedar">
                            Recent failure trend
                        </h2>
                    </div>
                    {data.recentFailureTrend.length > 0 ? (
                        <div className="space-y-3">
                            {data.recentFailureTrend.map((run) => (
                                <div
                                    key={run.id}
                                    className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-b border-copper/10 pb-3 last:border-b-0 last:pb-0"
                                >
                                    <div>
                                        <p className="font-dmSans text-body font-semibold text-cedar">
                                            {formatDateTime(run.exportedAt)}
                                        </p>
                                        <p className="font-dmSans text-caption text-soft-charcoal">
                                            {run.errorsTotal} error
                                            {run.errorsTotal === 1 ? "" : "s"}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <p className="font-gilroy-bold text-h3 text-copper">
                                            {run.clubsFailed}
                                        </p>
                                        <p className="font-dmSans text-caption text-soft-charcoal">
                                            failed
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <EmptyQueue />
                    )}
                </div>

                <div className="rounded-lg border border-copper/15 bg-white p-5 shadow-sm">
                    <div className="mb-4 flex items-center gap-3">
                        <Bot className="h-5 w-5 text-copper" />
                        <h2 className="font-gilroy-bold text-h3 text-cedar">
                            Latest failed club runs
                        </h2>
                    </div>
                    {data.latestFailedClubs.length > 0 ? (
                        <div className="space-y-3">
                            {data.latestFailedClubs.map((club) => (
                                <div
                                    key={`${club.clubId ?? club.clubName}-${club.errorMessage ?? "error"}`}
                                    className="rounded-md bg-ecru-white px-3 py-3"
                                >
                                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                                        <div>
                                            <ClubLink clubId={club.clubId}>
                                                {club.clubName}
                                            </ClubLink>
                                            <p className="mt-1 font-dmSans text-caption text-soft-charcoal">
                                                {club.errorMessage ??
                                                    "No error message captured"}
                                            </p>
                                        </div>
                                        {club.botBlockDetected && (
                                            <span className="inline-flex w-fit items-center gap-1 rounded-md bg-copper/10 px-2 py-1 font-dmSans text-caption font-semibold text-copper">
                                                <Bot className="h-3.5 w-3.5" />
                                                Bot block
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <EmptyQueue />
                    )}
                </div>
            </section>

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <QueueShell
                    title="Stale scraper keys"
                    count={outliers.staleScraperKeys.length}
                    icon={RadioTower}
                >
                    {outliers.staleScraperKeys.length > 0 ? (
                        <ul className="space-y-3">
                            {outliers.staleScraperKeys.map((row) => (
                                <li key={row.scraperKey}>
                                    <p className="font-dmSans text-body font-semibold text-cedar">
                                        {row.scraperKey}
                                    </p>
                                    <p className="font-dmSans text-caption text-soft-charcoal">
                                        {row.enabledSourceCount} enabled source
                                        {row.enabledSourceCount === 1
                                            ? ""
                                            : "s"}{" "}
                                        without 7-day writes
                                    </p>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <EmptyQueue />
                    )}
                </QueueShell>

                <QueueShell
                    title="Source issues"
                    count={outliers.sourceIssues.length}
                    icon={CircleHelp}
                >
                    {outliers.sourceIssues.length > 0 ? (
                        <ul className="space-y-3">
                            {outliers.sourceIssues.map((row) => (
                                <li
                                    key={`${row.clubId}-${row.platform}-${row.issue}`}
                                >
                                    <ClubLink clubId={row.clubId}>
                                        {row.clubName}
                                    </ClubLink>
                                    <p className="font-dmSans text-caption text-soft-charcoal">
                                        {row.platform}: {row.issue}
                                    </p>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <EmptyQueue />
                    )}
                </QueueShell>

                <QueueShell
                    title="Clubs without future shows"
                    count={outliers.clubsWithoutFutureShows.length}
                    icon={CalendarX2}
                >
                    {outliers.clubsWithoutFutureShows.length > 0 ? (
                        <ul className="space-y-3">
                            {outliers.clubsWithoutFutureShows.map((row) => (
                                <li key={row.clubId}>
                                    <ClubLink clubId={row.clubId}>
                                        {row.clubName}
                                    </ClubLink>
                                    <p className="font-dmSans text-caption text-soft-charcoal">
                                        {[row.city, row.state]
                                            .filter(Boolean)
                                            .join(", ") || "Location missing"}
                                    </p>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <EmptyQueue />
                    )}
                </QueueShell>

                <QueueShell
                    title="Incomplete shows"
                    count={outliers.incompleteShows.length}
                    icon={FileWarning}
                >
                    {outliers.incompleteShows.length > 0 ? (
                        <ul className="space-y-3">
                            {outliers.incompleteShows.map((row) => (
                                <li key={row.showId}>
                                    <Link
                                        href={`/show/${row.showId}`}
                                        className="font-semibold text-copper hover:underline"
                                    >
                                        {row.showName ?? "Untitled show"}
                                    </Link>
                                    <p className="font-dmSans text-caption text-soft-charcoal">
                                        {row.clubName}: missing{" "}
                                        {row.missingFields.join(", ")}
                                    </p>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <EmptyQueue />
                    )}
                </QueueShell>

                <QueueShell
                    title="Missing metadata"
                    count={outliers.missingMetadata.length}
                    icon={ClipboardList}
                >
                    {outliers.missingMetadata.length > 0 ? (
                        <ul className="space-y-3">
                            {outliers.missingMetadata.map((row) => (
                                <li key={row.clubId}>
                                    <ClubLink clubId={row.clubId}>
                                        {row.clubName}
                                    </ClubLink>
                                    <p className="font-dmSans text-caption text-soft-charcoal">
                                        Missing {row.missingFields.join(", ")}
                                    </p>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <EmptyQueue />
                    )}
                </QueueShell>

                <QueueShell
                    title="Pending reviews"
                    count={outliers.pendingReviews.length}
                    icon={ListChecks}
                >
                    {outliers.pendingReviews.length > 0 ? (
                        <ul className="space-y-3">
                            {outliers.pendingReviews.map((row) => (
                                <li key={row.queue}>
                                    <p className="font-dmSans text-body font-semibold text-cedar">
                                        {row.queue}
                                    </p>
                                    <p className="font-dmSans text-caption text-soft-charcoal">
                                        {row.count} pending, oldest{" "}
                                        {formatDateTime(row.oldestCreatedAt)}
                                    </p>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <EmptyQueue />
                    )}
                </QueueShell>
            </section>
        </div>
    );
}

function Metric({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-md bg-white/80 px-3 py-3">
            <p className="font-gilroy-bold text-h2 leading-tight text-cedar">
                {value}
            </p>
            <p className="font-dmSans text-caption text-soft-charcoal">
                {label}
            </p>
        </div>
    );
}

function MetricBand({
    label,
    value,
    icon: Icon,
}: {
    label: string;
    value: string;
    icon: typeof AlertTriangle;
}) {
    return (
        <div className="rounded-lg border border-copper/15 bg-white px-4 py-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between gap-3">
                <p className="font-dmSans text-caption font-semibold uppercase text-soft-charcoal">
                    {label}
                </p>
                <Icon className="h-4 w-4 text-copper" />
            </div>
            <p className="font-gilroy-bold text-h2 text-cedar">{value}</p>
        </div>
    );
}
