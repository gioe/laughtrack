"use client";

import { Check, ExternalLink, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { Button } from "@/ui/components/ui/button";
import type { AdminPodcastOwnershipReviewCandidate } from "@/lib/admin/podcastOwnershipReviews";

export type { AdminPodcastOwnershipReviewCandidate };

type Decision = "accept" | "reject";

type Status = {
    kind: "idle" | "ok" | "error";
    message?: string;
};

type Props = {
    candidates: AdminPodcastOwnershipReviewCandidate[];
};

function formatPercent(value: number) {
    return `${Math.round(value * 100)}%`;
}

function formatDate(iso: string) {
    return iso.replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

function evidencePreview(evidence: unknown) {
    if (!evidence || typeof evidence !== "object") return "No evidence";
    return JSON.stringify(evidence, null, 2);
}

export default function AdminPodcastOwnershipReviewManager({
    candidates,
}: Props) {
    const router = useRouter();
    const [notes, setNotes] = useState<Record<number, string>>({});
    const [pendingCandidateId, setPendingCandidateId] = useState<number | null>(
        null,
    );
    const [status, setStatus] = useState<Status>({ kind: "idle" });
    const [isPending, startTransition] = useTransition();

    async function decide(candidateId: number, action: Decision) {
        const reason = notes[candidateId]?.trim() ?? "";
        setStatus({ kind: "idle" });
        setPendingCandidateId(candidateId);

        let res: Response;
        try {
            res = await fetch("/api/admin/podcast-ownership-reviews", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ candidateId, action, reason }),
            });
        } catch (error) {
            setPendingCandidateId(null);
            setStatus({
                kind: "error",
                message:
                    error instanceof Error ? error.message : "Network error",
            });
            return;
        }

        setPendingCandidateId(null);
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            setStatus({
                kind: "error",
                message: body.error ?? `Request failed (${res.status})`,
            });
            return;
        }

        setStatus({
            kind: "ok",
            message:
                action === "accept"
                    ? "Candidate accepted."
                    : "Candidate rejected.",
        });
        startTransition(() => router.refresh());
    }

    if (candidates.length === 0) {
        return (
            <div className="rounded-md border border-copper/25 bg-white p-6 font-dmSans text-body text-soft-charcoal">
                No pending podcast ownership candidates.
            </div>
        );
    }

    return (
        <div className="space-y-5">
            {status.kind === "ok" && (
                <p className="rounded-md border border-green-200 bg-green-50 px-4 py-3 font-dmSans text-sm text-green-800">
                    {status.message}
                </p>
            )}
            {status.kind === "error" && (
                <p className="rounded-md border border-red-200 bg-red-50 px-4 py-3 font-dmSans text-sm text-red-800">
                    {status.message}
                </p>
            )}
            <ul className="divide-y divide-gray-300 rounded-md border border-gray-300 bg-white">
                {candidates.map((candidate) => {
                    const noteId = `podcast-review-note-${candidate.id}`;
                    const isCurrent = pendingCandidateId === candidate.id;
                    const disabled =
                        isPending || pendingCandidateId !== null || isCurrent;
                    return (
                        <li key={candidate.id} className="grid gap-4 p-4">
                            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,360px)]">
                                <div className="min-w-0">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <h2 className="font-gilroy-bold text-h3 leading-tight text-cedar">
                                            {candidate.comedian.name}
                                        </h2>
                                        <span className="rounded-md bg-coconut-cream px-2 py-1 font-dmSans text-caption text-soft-charcoal">
                                            {formatPercent(
                                                candidate.confidence,
                                            )}
                                        </span>
                                        {candidate.associationType && (
                                            <span className="rounded-md bg-american-silver/60 px-2 py-1 font-dmSans text-caption text-cedar">
                                                {candidate.associationType}
                                            </span>
                                        )}
                                    </div>
                                    <div className="mt-2 font-dmSans text-body text-soft-charcoal">
                                        {candidate.podcast ? (
                                            <>
                                                <span className="font-semibold text-cedar">
                                                    {candidate.podcast.title}
                                                </span>
                                                {candidate.podcast
                                                    .authorName && (
                                                    <span>
                                                        {" "}
                                                        by{" "}
                                                        {
                                                            candidate.podcast
                                                                .authorName
                                                        }
                                                    </span>
                                                )}
                                            </>
                                        ) : (
                                            <span>No podcast row linked</span>
                                        )}
                                    </div>
                                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-dmSans text-caption text-soft-charcoal">
                                        <span>{candidate.source}</span>
                                        <span>{candidate.sourcePodcastId}</span>
                                        <time dateTime={candidate.createdAt}>
                                            {formatDate(candidate.createdAt)}
                                        </time>
                                    </div>
                                    {candidate.podcast && (
                                        <div className="mt-3 flex flex-wrap gap-3 font-dmSans text-caption">
                                            <a
                                                href={`/podcast/${candidate.podcast.slug}`}
                                                className="inline-flex items-center gap-1 text-copper hover:underline"
                                            >
                                                Public page
                                                <ExternalLink
                                                    className="h-3.5 w-3.5"
                                                    aria-hidden="true"
                                                />
                                            </a>
                                            {candidate.podcast.websiteUrl && (
                                                <a
                                                    href={
                                                        candidate.podcast
                                                            .websiteUrl
                                                    }
                                                    className="inline-flex items-center gap-1 text-copper hover:underline"
                                                >
                                                    Website
                                                    <ExternalLink
                                                        className="h-3.5 w-3.5"
                                                        aria-hidden="true"
                                                    />
                                                </a>
                                            )}
                                        </div>
                                    )}
                                </div>

                                <div className="grid gap-3">
                                    <label
                                        htmlFor={noteId}
                                        className="grid gap-1 font-dmSans text-sm font-semibold text-cedar"
                                    >
                                        Review note for{" "}
                                        {candidate.comedian.name}
                                        <textarea
                                            id={noteId}
                                            value={notes[candidate.id] ?? ""}
                                            onChange={(event) =>
                                                setNotes((prev) => ({
                                                    ...prev,
                                                    [candidate.id]:
                                                        event.target.value,
                                                }))
                                            }
                                            className="min-h-20 rounded-md border border-gray-300 px-3 py-2 font-dmSans text-body font-normal text-foreground focus:border-copper focus:outline-none focus:ring-2 focus:ring-copper"
                                            maxLength={1000}
                                        />
                                    </label>
                                    <div className="flex gap-2">
                                        <Button
                                            type="button"
                                            className="gap-2"
                                            variant="roundedShimmer"
                                            onClick={() =>
                                                void decide(
                                                    candidate.id,
                                                    "accept",
                                                )
                                            }
                                            disabled={
                                                disabled ||
                                                candidate.podcast === null
                                            }
                                            aria-label={`Accept ${candidate.comedian.name}`}
                                        >
                                            <Check
                                                className="h-4 w-4"
                                                aria-hidden="true"
                                            />
                                            Accept
                                        </Button>
                                        <Button
                                            type="button"
                                            className="gap-2"
                                            variant="outline"
                                            onClick={() =>
                                                void decide(
                                                    candidate.id,
                                                    "reject",
                                                )
                                            }
                                            disabled={disabled}
                                            aria-label={`Reject ${candidate.comedian.name}`}
                                        >
                                            <X
                                                className="h-4 w-4"
                                                aria-hidden="true"
                                            />
                                            Reject
                                        </Button>
                                    </div>
                                </div>
                            </div>

                            <details className="rounded-md bg-ecru-white p-3">
                                <summary className="cursor-pointer font-dmSans text-sm font-semibold text-cedar">
                                    Evidence and ownership context
                                </summary>
                                <pre className="mt-3 overflow-auto whitespace-pre-wrap break-words font-mono text-xs text-soft-charcoal">
                                    {evidencePreview(candidate.evidence)}
                                </pre>
                                {candidate.existingOwnerships.length > 0 && (
                                    <ul className="mt-3 grid gap-2 font-dmSans text-caption text-soft-charcoal">
                                        {candidate.existingOwnerships.map(
                                            (ownership) => (
                                                <li key={ownership.id}>
                                                    {ownership.associationType}{" "}
                                                    · {ownership.source} ·{" "}
                                                    {ownership.reviewStatus} ·{" "}
                                                    {formatPercent(
                                                        ownership.confidence,
                                                    )}
                                                </li>
                                            ),
                                        )}
                                    </ul>
                                )}
                            </details>
                        </li>
                    );
                })}
            </ul>
        </div>
    );
}
