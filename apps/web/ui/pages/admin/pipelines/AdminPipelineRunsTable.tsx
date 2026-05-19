"use client";

import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import { Fragment } from "react";
import { useState } from "react";
import type { AdminPipelineRun } from "@/lib/admin/pipelines";

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

function DetailItem({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <dt className="font-semibold text-cedar">{label}</dt>
            <dd className="break-words text-soft-charcoal">{value}</dd>
        </div>
    );
}

function isGithubActionsRun(run: AdminPipelineRun) {
    return run.source?.startsWith("github_actions") ?? false;
}

function shortSha(value: string | null) {
    return value ? value.slice(0, 12) : null;
}

export default function AdminPipelineRunsTable({
    runs,
}: {
    runs: AdminPipelineRun[];
}) {
    const [openRunIds, setOpenRunIds] = useState<Set<number>>(new Set());

    function toggleRun(runId: number) {
        setOpenRunIds((current) => {
            const next = new Set(current);
            if (next.has(runId)) {
                next.delete(runId);
            } else {
                next.add(runId);
            }
            return next;
        });
    }

    return (
        <section className="overflow-hidden rounded-md border border-copper/20 bg-white">
            <div className="border-b border-copper/15 bg-cedar px-4 py-3">
                <h2 className="font-gilroy-bold text-h3 text-coconut-cream">
                    Recent runs
                </h2>
            </div>
            {runs.length === 0 ? (
                <p className="p-4 font-dmSans text-body text-soft-charcoal">
                    No recent runs found.
                </p>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full min-w-[980px] text-left font-dmSans text-body">
                        <thead className="bg-ecru-white text-caption uppercase text-soft-charcoal">
                            <tr>
                                <th className="px-4 py-3">Pipeline</th>
                                <th className="px-4 py-3">Status</th>
                                <th className="px-4 py-3">Exported</th>
                                <th className="px-4 py-3">Duration</th>
                                <th className="px-4 py-3">Success</th>
                                <th className="px-4 py-3">Clubs</th>
                                <th className="px-4 py-3">Shows</th>
                                <th className="px-4 py-3">Errors</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-copper/15">
                            {runs.map((run) => {
                                const isOpen = openRunIds.has(run.id);
                                const isGithubRun = isGithubActionsRun(run);
                                return (
                                    <Fragment key={run.id}>
                                        <tr className="hover:bg-ecru-white/60">
                                            <td className="px-4 py-3 font-semibold text-cedar">
                                                <button
                                                    type="button"
                                                    className="flex max-w-[360px] items-start gap-2 text-left text-cedar"
                                                    aria-expanded={isOpen}
                                                    aria-controls={`pipeline-run-${run.id}`}
                                                    onClick={() =>
                                                        toggleRun(run.id)
                                                    }
                                                >
                                                    <span className="mt-1 text-copper-dark">
                                                        {isOpen ? (
                                                            <ChevronDown className="h-4 w-4" />
                                                        ) : (
                                                            <ChevronRight className="h-4 w-4" />
                                                        )}
                                                    </span>
                                                    <span>
                                                        <span className="block">
                                                            {run.pipelineName}
                                                        </span>
                                                        <span className="block break-all font-dmSans text-caption font-normal text-soft-charcoal">
                                                            {run.runKey}
                                                        </span>
                                                    </span>
                                                </button>
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
                                                {formatSeconds(
                                                    run.durationSeconds,
                                                )}
                                            </td>
                                            <td className="px-4 py-3 text-soft-charcoal">
                                                {formatPercent(run.successRate)}
                                            </td>
                                            <td className="px-4 py-3 text-soft-charcoal">
                                                {isGithubRun
                                                    ? "N/A"
                                                    : `${run.clubsSuccessful}/${run.clubsProcessed} ok`}
                                            </td>
                                            <td className="px-4 py-3 text-soft-charcoal">
                                                {isGithubRun
                                                    ? "N/A"
                                                    : `${run.showsSaved.toLocaleString()} saved`}
                                            </td>
                                            <td className="px-4 py-3 text-soft-charcoal">
                                                {run.errorsTotal.toLocaleString()}
                                            </td>
                                        </tr>
                                        {isOpen && (
                                            <tr id={`pipeline-run-${run.id}`}>
                                                <td
                                                    colSpan={8}
                                                    className="bg-ecru-white/70 px-4 py-4"
                                                >
                                                    <div className="grid gap-4 font-dmSans text-body md:grid-cols-3">
                                                        <dl className="grid gap-2">
                                                            <DetailItem
                                                                label="Run key"
                                                                value={
                                                                    run.runKey
                                                                }
                                                            />
                                                            <DetailItem
                                                                label="Source"
                                                                value={
                                                                    run.source ??
                                                                    "scraper"
                                                                }
                                                            />
                                                            <DetailItem
                                                                label="Exported"
                                                                value={formatDateTime(
                                                                    run.exportedAt,
                                                                )}
                                                            />
                                                        </dl>
                                                        {isGithubRun ? (
                                                            <dl className="grid gap-2">
                                                                <DetailItem
                                                                    label="Workflow"
                                                                    value={
                                                                        run.workflowName ??
                                                                        run.pipelineName
                                                                    }
                                                                />
                                                                <DetailItem
                                                                    label="Title"
                                                                    value={
                                                                        run.displayTitle ??
                                                                        "Not recorded"
                                                                    }
                                                                />
                                                                <DetailItem
                                                                    label="Event"
                                                                    value={
                                                                        run.event ??
                                                                        "Not recorded"
                                                                    }
                                                                />
                                                                <DetailItem
                                                                    label="Actor"
                                                                    value={
                                                                        run.actor ??
                                                                        "Not recorded"
                                                                    }
                                                                />
                                                                <DetailItem
                                                                    label="Run number"
                                                                    value={
                                                                        run.runNumber ??
                                                                        "Not recorded"
                                                                    }
                                                                />
                                                                <DetailItem
                                                                    label="Attempt"
                                                                    value={
                                                                        run.runAttempt ??
                                                                        "Not recorded"
                                                                    }
                                                                />
                                                                <DetailItem
                                                                    label="Ref"
                                                                    value={
                                                                        run.ref ??
                                                                        "Not recorded"
                                                                    }
                                                                />
                                                                <DetailItem
                                                                    label="SHA"
                                                                    value={
                                                                        shortSha(
                                                                            run.sha,
                                                                        ) ??
                                                                        "Not recorded"
                                                                    }
                                                                />
                                                            </dl>
                                                        ) : (
                                                            <dl className="grid gap-2">
                                                                <DetailItem
                                                                    label="Shows scraped"
                                                                    value={run.showsScraped.toLocaleString()}
                                                                />
                                                                <DetailItem
                                                                    label="Shows inserted"
                                                                    value={run.showsInserted.toLocaleString()}
                                                                />
                                                                <DetailItem
                                                                    label="Shows updated"
                                                                    value={run.showsUpdated.toLocaleString()}
                                                                />
                                                                <DetailItem
                                                                    label="Shows failed save"
                                                                    value={run.showsFailedSave.toLocaleString()}
                                                                />
                                                                <DetailItem
                                                                    label="Skipped duplicates"
                                                                    value={run.showsSkippedDedup.toLocaleString()}
                                                                />
                                                                <DetailItem
                                                                    label="Validation failures"
                                                                    value={run.showsValidationFailed.toLocaleString()}
                                                                />
                                                                <DetailItem
                                                                    label="DB errors"
                                                                    value={run.showsDbErrors.toLocaleString()}
                                                                />
                                                            </dl>
                                                        )}
                                                        <dl className="grid gap-2">
                                                            {run.runUrl && (
                                                                <div>
                                                                    <dt className="font-semibold text-cedar">
                                                                        Run URL
                                                                    </dt>
                                                                    <dd>
                                                                        <a
                                                                            href={
                                                                                run.runUrl
                                                                            }
                                                                            target="_blank"
                                                                            rel="noreferrer"
                                                                            className="inline-flex items-center gap-1 break-all font-semibold text-copper-dark hover:underline"
                                                                        >
                                                                            Open
                                                                            run
                                                                            <ExternalLink className="h-4 w-4" />
                                                                        </a>
                                                                    </dd>
                                                                </div>
                                                            )}
                                                        </dl>
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </Fragment>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </section>
    );
}
