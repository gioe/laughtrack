import {
    eventReviewFilters,
    getEventReview,
    listEventReviews,
    type EventReviewDetail,
    type EventReviewRow,
} from "./eventReviews";
import type { ReviewItem, ReviewPage } from "./reviewTypes";
import type { z } from "zod";
function text(value: unknown, fallback = "Not provided"): string {
    return typeof value === "string" && value.trim() ? value : fallback;
}
function records(value: unknown): Record<string, unknown>[] {
    return Array.isArray(value)
        ? value.filter(
              (v): v is Record<string, unknown> => !!v && typeof v === "object",
          )
        : [];
}
function words(value: unknown): string {
    return Array.isArray(value)
        ? value
              .filter((v) => typeof v === "string")
              .join(", ")
              .replaceAll("_", " ")
        : "";
}
export function screeningEffect(row: EventReviewRow) {
    if (row.gate_mode === "off")
        return "Screening off · observation only. Reviews are read-only.";
    if (!row.enabled)
        return "Source disabled · no new ingestion. Reviews are read-only.";
    if (
        ["reject", "defer", "stale_review"].includes(row.status) &&
        row.review_version > 0
    )
        return "Human hold · withheld on the next scrape, including in shadow mode.";
    if (row.gate_mode === "shadow")
        return "Shadow mode · automated flags alone do not withhold events.";
    return "Enforcement on · only accepted or currently approved events may pass the next scrape.";
}
export function eventReviewItem(
    row: EventReviewRow,
    detail?: EventReviewDetail,
): ReviewItem {
    const p = row.payload ?? {},
        e = row.evidence ?? {};
    const pending =
        row.request_status === "pending" ||
        !!detail?.requests.some((r) => r.status === "pending");
    const eligible =
        row.enabled &&
        row.gate_mode !== "off" &&
        !!row.decision_id &&
        row.policy_version === row.current_policy_version;
    const item: ReviewItem = {
        id: String(row.candidate_id),
        workflow: "event_eligibility",
        title: text(p.name, "Untitled event"),
        subtitle: [
            row.club_name,
            text(p.date, "Date unavailable"),
            row.status.replaceAll("_", " "),
        ].join(" · "),
        status: row.status as ReviewItem["status"],
        token: row.token,
        actions: eligible && !pending ? ["approve", "reject", "defer"] : [],
        processing: pending,
        notice: [
            screeningEffect(row),
            pending
                ? "Review submitted; awaiting worker validation."
                : !eligible
                  ? "Current evidence or policy is not ready for a decision. Refresh after the next observation."
                  : "Decisions are validated by the worker; publication is checked on the next scrape. Existing listings do not change immediately.",
        ].join(" "),
        matches: [],
        history: [],
        evidence: [],
    };
    if (!detail) return item;
    item.evidence = [
        {
            id: "event",
            title: "Event description",
            context: text(p.description),
            url: text(p.url, "") || null,
            source: row.club_name,
            kind: "Event",
            date: text(p.date, "") || undefined,
        },
        {
            id: "reasons",
            title: "Why it was flagged",
            context: `${words(e.reason_codes) || "No rule reasons recorded."}\nClassifier: ${row.decision ?? "awaiting observation"}. Review state: ${row.status.replaceAll("_", " ")}.`,
            url: null,
            source: row.scraper_key,
            kind: row.source_policy,
        },
        ...records(e.evidence).map((v, i) => ({
            id: `evidence-${i}`,
            title: text(v.kind),
            context: text(v.detail),
            url: null,
            source: row.scraper_key,
            kind: text(v.provenance),
        })),
        {
            id: "lineup",
            title: "Lineup and parent identities",
            context: [
                `Coverage: ${text(e.lineup_status, "unknown")}. Identity checks run again before applying a review.`,
                ...records(e.performers).map((v) =>
                    [
                        words(v.names) || "Unnamed performer",
                        text(v.state),
                        v.canonical_id != null
                            ? `Resolved comedian ID: ${String(v.canonical_id)}`
                            : "",
                        words(v.block_reasons),
                        words(v.diagnostics),
                    ]
                        .filter(Boolean)
                        .join(" · "),
                ),
                "An alias resolving to a parent is identity evidence; it does not by itself establish comedy.",
            ].join("\n"),
            url: null,
            source: row.club_name,
            kind: "Performer evidence",
        },
    ];
    item.history = [
        ...detail.requests.map((v) => ({
            id: `request-${v.id}`,
            action: v.action,
            reason: [v.reason, v.error].filter(Boolean).join(" · "),
            actor: v.actor,
            createdAt: v.created_at,
            undone: false,
            status: v.status,
        })),
        ...detail.history.map((v, i) => ({
            id: `review-${i}`,
            action: text(v.action),
            reason: text(v.reason),
            actor: text(v.actor),
            createdAt: text(v.created_at, ""),
            undone: false,
            status: "applied",
        })),
        ...detail.observations.map((v, i) => ({
            id: `observation-${i}`,
            action: "Observation",
            reason: `${text(v.decision)} · ${text(v.classifier_version)}`,
            actor: "Screening",
            createdAt: text(v.observed_at, ""),
            undone: false,
        })),
        ...detail.publications.map((v, i) => ({
            id: `publication-${i}`,
            action: "Past publication",
            reason: `Show ${String(v.show_id)}. Historical link; not a statement of current publication.`,
            actor: "Ingestion",
            createdAt: text(v.published_at, ""),
            undone: false,
        })),
    ].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
    return item;
}
export async function listEventInbox(
    input: z.input<typeof eventReviewFilters>,
    page: number,
): Promise<ReviewPage> {
    const result = await listEventReviews(input);
    return {
        items: result.items.map((row) => eventReviewItem(row)),
        total: null,
        page,
        cursor: { ceiling: result.ceiling, next: result.next },
    };
}
export async function getEventInbox(id: string) {
    const detail = await getEventReview(Number(id));
    return detail ? eventReviewItem(detail.current, detail) : null;
}
