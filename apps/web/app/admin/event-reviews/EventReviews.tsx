"use client";
import { useEffect, useRef, useState } from "react";
import type {
    EventReviewDetail,
    EventReviewPage,
    EventReviewRow,
    ReviewSubmission,
} from "@/lib/admin/eventReviews";

const field =
    "rounded-md border border-copper/30 bg-surface px-3 py-2 text-foreground focus:border-copper focus:ring-2 focus:ring-copper/30";
const button =
    "rounded-md border border-copper/40 px-3 py-2 font-semibold text-copper hover:bg-copper/10 disabled:opacity-50";
const panel = "space-y-4 rounded-md border border-copper/20 bg-surface p-4";
function text(value: unknown, fallback = "Not provided"): string {
    return typeof value === "string" && value.trim() ? value : fallback;
}
function records(value: unknown): Record<string, unknown>[] {
    return Array.isArray(value)
        ? value.filter((v) => v && typeof v === "object")
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
function label(value: string) {
    return value.replaceAll("_", " ");
}
function date(value: unknown) {
    const raw = text(value, "");
    const d = new Date(raw);
    return Number.isNaN(d.getTime())
        ? "Date unavailable"
        : d.toLocaleString(undefined, { timeZoneName: "short" });
}
export function sourceUrl(value: unknown): string | null {
    try {
        const url = new URL(text(value, ""));
        return ["https:", "http:"].includes(url.protocol) ? url.href : null;
    } catch {
        return null;
    }
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
async function request<T>(url: string, options?: RequestInit): Promise<T> {
    const res = await fetch(url, { ...options, cache: "no-store" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Request failed");
    return data;
}
function EventEvidence({ detail }: { detail: EventReviewDetail }) {
    const { current: row } = detail;
    const payload = row.payload ?? {};
    const evidence = row.evidence ?? {};
    const url = sourceUrl(payload.url);
    return (
        <>
            <div>
                <h2 className="font-chivo text-h2">
                    {text(payload.name, "Untitled event")}
                </h2>
                <p>
                    {row.club_name} · {date(payload.date)}
                </p>
                <p className="text-caption text-muted-foreground">
                    {row.scraper_key} · source {row.source_id} ·{" "}
                    {label(row.source_policy)}
                </p>
                {url && (
                    <a
                        className="text-copper underline"
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        Open source event
                    </a>
                )}
            </div>
            <p className="rounded-md bg-surface-elevated p-3">
                {screeningEffect(row)}
            </p>
            <p>
                Classifier:{" "}
                <strong>{row.decision ?? "Awaiting observation"}</strong> ·
                Review state: <strong>{label(row.status)}</strong>
            </p>
            <section>
                <h3 className="font-semibold">Why it was flagged</h3>
                <p>
                    {words(evidence.reason_codes) ||
                        "No rule reasons recorded."}
                </p>
            </section>
            <section>
                <h3 className="font-semibold">Event description</h3>
                <p className="whitespace-pre-wrap break-words">
                    {text(payload.description)}
                </p>
            </section>
            <section>
                <h3 className="font-semibold">Collected evidence</h3>
                <ul className="space-y-2">
                    {records(evidence.evidence).map((e, i) => (
                        <li
                            key={i}
                            className="rounded-md bg-surface-elevated p-3"
                        >
                            <strong>{text(e.kind)}</strong> ·{" "}
                            {label(text(e.provenance))}
                            <p className="whitespace-pre-wrap break-words">
                                {text(e.detail)}
                            </p>
                        </li>
                    ))}
                </ul>
            </section>
            <section>
                <h3 className="font-semibold">Lineup and parent identities</h3>
                <p>
                    Coverage: {text(evidence.lineup_status, "unknown")}.
                    Identity checks run again before applying a review.
                </p>
                {records(evidence.performers).length === 0 ? (
                    <p>No resolved performers recorded.</p>
                ) : (
                    <ul className="space-y-2">
                        {records(evidence.performers).map((p, i) => (
                            <li
                                className="rounded-md bg-surface-elevated p-3"
                                key={i}
                            >
                                <strong>
                                    {words(p.names) || "Unnamed performer"}
                                </strong>{" "}
                                · {text(p.state)}
                                {p.canonical_id != null && (
                                    <p>
                                        Resolved comedian ID:{" "}
                                        {String(p.canonical_id)}
                                    </p>
                                )}
                                <p>{words(p.block_reasons)}</p>
                                <p>{words(p.diagnostics)}</p>
                            </li>
                        ))}
                    </ul>
                )}
                <p className="text-caption text-muted-foreground">
                    An alias resolving to a parent is identity evidence; it does
                    not by itself establish comedy.
                </p>
            </section>
            <section>
                <h3 className="font-semibold">Review requests</h3>
                {detail.requests.length === 0 ? (
                    <p>No admin requests yet.</p>
                ) : (
                    <ul className="space-y-2">
                        {detail.requests.map((r) => (
                            <li
                                key={r.id}
                                className="rounded-md bg-surface-elevated p-3"
                            >
                                <strong>
                                    {label(r.status)} · {r.action}
                                </strong>
                                <p>{r.reason}</p>
                                <p className="text-caption">
                                    {date(r.created_at)} · {r.actor}
                                </p>
                                {r.error && (
                                    <p className="text-copper">{r.error}</p>
                                )}
                            </li>
                        ))}
                    </ul>
                )}
            </section>
            <details>
                <summary className="cursor-pointer text-copper">
                    Decision and publication history (latest 100 each)
                </summary>
                <h3 className="mt-3 font-semibold">Applied reviews</h3>
                {detail.history.length === 0 ? (
                    <p>None recorded.</p>
                ) : (
                    detail.history.map((r, i) => (
                        <p key={i}>
                            {date(r.created_at)} · {text(r.action)} ·{" "}
                            {text(r.reason)} · {text(r.actor)}
                        </p>
                    ))
                )}
                <h3 className="mt-3 font-semibold">Observations</h3>
                {detail.observations.map((o, i) => (
                    <p key={i}>
                        {date(o.observed_at)} · {text(o.decision)} ·{" "}
                        {text(o.classifier_version)}
                    </p>
                ))}
                <h3 className="mt-3 font-semibold">Past publications</h3>
                <p>
                    These are historical links. Reviews do not immediately
                    remove or publish existing listings.
                </p>
                {detail.publications.length === 0 ? (
                    <p>No publication recorded.</p>
                ) : (
                    detail.publications.map((p, i) => (
                        <p key={i}>
                            Show {String(p.show_id)} · {date(p.published_at)}
                        </p>
                    ))
                )}
            </details>
        </>
    );
}
export default function EventReviews() {
    const [query, setQuery] = useState("");
    const [page, setPage] = useState<EventReviewPage | null>(null);
    const [selected, setSelected] = useState<number | null>(null);
    const [detail, setDetail] = useState<EventReviewDetail | null>(null);
    const [refresh, setRefresh] = useState(0);
    const [error, setError] = useState("");
    const [notice, setNotice] = useState("");
    const [busy, setBusy] = useState(false);
    const [action, setAction] = useState<ReviewSubmission["action"]>("approve");
    const [reason, setReason] = useState("");
    const [confirmation, setConfirmation] = useState<ReviewSubmission | null>(
        null,
    );
    const detailHeading = useRef<HTMLDivElement>(null);
    useEffect(() => {
        const controller = new AbortController();
        setPage(null);
        setError("");
        request<EventReviewPage>(`/api/admin/event-reviews?${query}`, {
            signal: controller.signal,
        })
            .then((result) => {
                if (!controller.signal.aborted) setPage(result);
            })
            .catch((e) => {
                if (!controller.signal.aborted) setError(e.message);
            });
        return () => controller.abort();
    }, [query, refresh]);
    useEffect(() => {
        const controller = new AbortController();
        setDetail(null);
        setConfirmation(null);
        setReason("");
        if (selected !== null)
            request<EventReviewDetail>(
                `/api/admin/event-reviews?id=${selected}`,
                { signal: controller.signal },
            )
                .then((d) => {
                    if (controller.signal.aborted) return;
                    setDetail(d);
                    detailHeading.current?.focus();
                })
                .catch((e) => {
                    if (!controller.signal.aborted) setError(e.message);
                });
        return () => controller.abort();
    }, [selected, refresh]);
    useEffect(() => {
        if (!detail?.requests.some((r) => r.status === "pending")) return;
        const timer = setInterval(() => setRefresh((v) => v + 1), 30000);
        return () => clearInterval(timer);
    }, [detail]);
    const groups = new Map<string, EventReviewRow[]>();
    for (const row of page?.items ?? []) {
        const key = JSON.stringify([
            row.club_id,
            row.source_id,
            text(row.payload?.name).toLowerCase(),
        ]);
        groups.set(key, [...(groups.get(key) ?? []), row]);
    }
    const row = detail?.current;
    const canReview =
        !!row &&
        row.enabled &&
        row.gate_mode !== "off" &&
        !!row.decision_id &&
        row.policy_version === row.current_policy_version &&
        !detail?.requests.some((r) => r.status === "pending");
    async function submit() {
        if (!confirmation || busy) return;
        setBusy(true);
        setError("");
        try {
            await request("/api/admin/event-reviews", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(confirmation),
            });
            setNotice(
                "Review submitted. The worker validates pending requests about every 15 minutes; scheduling can take longer. Publication is checked on the next scrape.",
            );
            setRefresh((v) => v + 1);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Submission failed");
        } finally {
            setBusy(false);
        }
    }
    return (
        <div className="space-y-6 font-dmSans">
            <form
                className="flex flex-wrap items-end gap-3 rounded-md border border-copper/20 bg-surface p-4"
                onSubmit={(e) => {
                    e.preventDefault();
                    const data = new FormData(e.currentTarget);
                    const p = new URLSearchParams();
                    for (const [k, v] of data)
                        if (String(v).trim()) p.set(k, String(v));
                    setSelected(null);
                    setNotice("");
                    setQuery(p.toString());
                    setRefresh((v) => v + 1);
                }}
            >
                <label className="flex flex-col gap-1">
                    Event or venue
                    <input name="q" className={field} maxLength={200} />
                </label>
                <label className="flex flex-col gap-1">
                    Source ID
                    <input
                        name="source"
                        type="number"
                        min="1"
                        className={field}
                    />
                </label>
                <label className="flex flex-col gap-1">
                    Screening mode
                    <select name="mode" className={field}>
                        <option value="">All modes</option>
                        {["off", "shadow", "enforce"].map((v) => (
                            <option key={v}>{v}</option>
                        ))}
                    </select>
                </label>
                <label className="flex flex-col gap-1">
                    Review state
                    <select name="status" className={field}>
                        <option value="">All states</option>
                        {[
                            "review",
                            "accept",
                            "reject",
                            "approve",
                            "defer",
                            "stale_review",
                            "stale_policy",
                            "awaiting_observation",
                        ].map((v) => (
                            <option value={v} key={v}>
                                {label(v)}
                            </option>
                        ))}
                    </select>
                </label>
                <button className={button} disabled={busy}>
                    Filter
                </button>
                <button
                    type="button"
                    className={button}
                    disabled={busy}
                    onClick={() => setRefresh((v) => v + 1)}
                >
                    Refresh
                </button>
            </form>
            {error && (
                <p role="alert" className="rounded-md border border-copper p-3">
                    {error}
                </p>
            )}
            {notice && (
                <p role="status" className="rounded-md bg-surface-elevated p-3">
                    {notice}
                </p>
            )}
            <div className="grid items-start gap-6 lg:grid-cols-2">
                <section className="space-y-3" aria-label="Event review queue">
                    {!page ? (
                        <p role="status">
                            {error
                                ? "Queue unavailable. Try Refresh."
                                : "Loading events…"}
                        </p>
                    ) : (
                        <>
                            <p className="text-caption text-muted-foreground">
                                {page.items.length} occurrences on this page.
                                Related titles are grouped within the page; each
                                occurrence is reviewed separately.
                            </p>
                            {page.items.length === 0 && (
                                <p>No events match these filters.</p>
                            )}
                            {Array.from(groups.entries()).map(
                                ([key, items]) => (
                                    <div key={key} className={panel}>
                                        <h2 className="font-semibold">
                                            {text(
                                                items[0].payload?.name,
                                                "Untitled event",
                                            )}
                                        </h2>
                                        <p>
                                            {items[0].club_name} ·{" "}
                                            {items[0].scraper_key}
                                        </p>
                                        <ul className="space-y-2">
                                            {items.map((item) => (
                                                <li key={item.candidate_id}>
                                                    <button
                                                        disabled={busy}
                                                        onClick={() => {
                                                            setSelected(
                                                                item.candidate_id,
                                                            );
                                                            setError("");
                                                            setNotice("");
                                                        }}
                                                        aria-pressed={
                                                            selected ===
                                                            item.candidate_id
                                                        }
                                                        className={`${button} w-full text-left`}
                                                    >
                                                        {date(
                                                            item.payload?.date,
                                                        )}{" "}
                                                        · {label(item.status)}
                                                        <span className="block text-caption">
                                                            {item.gate_mode}{" "}
                                                            mode
                                                            {item.request_status
                                                                ? ` · request ${item.request_status}`
                                                                : ""}
                                                        </span>
                                                    </button>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                ),
                            )}
                            <div className="flex gap-3">
                                <button
                                    className={button}
                                    disabled={
                                        busy ||
                                        !new URLSearchParams(query).has("after")
                                    }
                                    onClick={() => {
                                        const p = new URLSearchParams(query);
                                        p.delete("after");
                                        p.delete("ceiling");
                                        setQuery(p.toString());
                                    }}
                                >
                                    First page
                                </button>
                                {page.next !== null && (
                                    <button
                                        className={button}
                                        disabled={busy}
                                        onClick={() => {
                                            const p = new URLSearchParams(
                                                query,
                                            );
                                            p.set("after", String(page.next));
                                            p.set(
                                                "ceiling",
                                                String(page.ceiling),
                                            );
                                            setQuery(p.toString());
                                        }}
                                    >
                                        Next page
                                    </button>
                                )}
                            </div>
                        </>
                    )}
                </section>
                <section className={panel} aria-label="Selected event">
                    <div
                        ref={detailHeading}
                        tabIndex={-1}
                        className="space-y-4 outline-none"
                    >
                        {!detail ? (
                            <p>
                                {selected
                                    ? "Loading event evidence…"
                                    : "Select an occurrence to inspect its evidence."}
                            </p>
                        ) : (
                            <EventEvidence detail={detail} />
                        )}
                    </div>
                    {detail && (
                        <>
                            <p className="text-caption text-muted-foreground">
                                Reviews apply to this occurrence and its current
                                evidence. They do not change venue trust or
                                performer visibility. Reject and defer also hold
                                future ingestion in shadow mode.
                            </p>
                            {!canReview ? (
                                <p>
                                    Review unavailable: this source is off or
                                    disabled, its observation needs refreshing,
                                    or a request is pending.
                                </p>
                            ) : (
                                <form
                                    className="space-y-3"
                                    onSubmit={(e) => {
                                        e.preventDefault();
                                        if (row && reason.trim())
                                            setConfirmation({
                                                id: crypto.randomUUID(),
                                                candidateId: row.candidate_id,
                                                token: row.token,
                                                action,
                                                reason: reason.trim(),
                                            });
                                    }}
                                >
                                    <label className="flex flex-col gap-1">
                                        Decision
                                        <select
                                            className={field}
                                            value={action}
                                            disabled={!!confirmation}
                                            onChange={(e) =>
                                                setAction(
                                                    e.target
                                                        .value as ReviewSubmission["action"],
                                                )
                                            }
                                        >
                                            <option value="approve">
                                                Approve as comedy
                                            </option>
                                            <option value="reject">
                                                Reject from ingestion
                                            </option>
                                            <option value="defer">
                                                Defer — keep on hold
                                            </option>
                                        </select>
                                    </label>
                                    <label className="flex flex-col gap-1">
                                        Reason
                                        <textarea
                                            required
                                            maxLength={2000}
                                            className={field}
                                            value={reason}
                                            disabled={!!confirmation}
                                            onChange={(e) =>
                                                setReason(e.target.value)
                                            }
                                        />
                                    </label>
                                    {!confirmation && (
                                        <button
                                            className={button}
                                            disabled={!reason.trim()}
                                        >
                                            Preview decision
                                        </button>
                                    )}
                                </form>
                            )}
                            {confirmation && (
                                <div
                                    className="space-y-3 rounded-md border border-copper p-4"
                                    aria-label="Confirm event review"
                                >
                                    <h3 className="font-semibold">
                                        Confirm {confirmation.action} for this
                                        occurrence
                                    </h3>
                                    <p>
                                        {text(row?.payload?.name)} ·{" "}
                                        {date(row?.payload?.date)}
                                    </p>
                                    <p>{confirmation.reason}</p>
                                    <p>
                                        The worker will recheck the evidence
                                        before applying this decision.
                                    </p>
                                    <div className="flex gap-3">
                                        <button
                                            className={button}
                                            disabled={busy}
                                            onClick={submit}
                                        >
                                            {busy
                                                ? "Submitting…"
                                                : "Confirm review"}
                                        </button>
                                        <button
                                            className={button}
                                            disabled={busy}
                                            onClick={() =>
                                                setConfirmation(null)
                                            }
                                        >
                                            Edit decision
                                        </button>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </section>
            </div>
        </div>
    );
}
