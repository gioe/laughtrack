"use client";
import { useEffect, useRef, useState } from "react";
import ReviewWorkspace from "./ReviewWorkspace";
import { RelationshipProposal } from "./RelationshipProposal";
import type {
    InboxDetail,
    InboxPage,
    InboxPreview,
    InboxAction,
} from "@/lib/admin/curation/inboxTypes";
import {
    availableActions,
    actionLabels,
} from "@/lib/admin/curation/inboxTypes";
import type { Command } from "@/lib/admin/curation/decisions";
import { button, field, inboxRequest } from "./inboxClient";
type Pending = {
    url: string;
    body: Record<string, unknown>;
    requestId: string;
    preview: InboxPreview;
    label: string;
};
const kindLabels: Record<string, string> = {
    all: "All types",
    comedian: "Comedians",
    club: "Clubs",
    show: "Shows",
    podcast: "Podcasts",
    alias_of: "Parent / child",
    host_of: "Host",
    cohost_of: "Cohost",
};
const stateLabels: Record<string, string> = {
    all: "All states",
    pending: "Needs review",
    proposed: "Proposed",
    approved: "Approved",
    blocked: "Blocked",
    confirmed: "Confirmed",
    rejected: "Rejected",
    severed: "Severed",
};
const storageKey = "curation-inbox-request-v1";
function safeUrl(value: unknown) {
    if (typeof value !== "string") return null;
    try {
        const u = new URL(value);
        return ["http:", "https:"].includes(u.protocol) ? u.href : null;
    } catch {
        return null;
    }
}
function Evidence({ value }: { value: unknown }) {
    if (value === null) return <span>—</span>;
    if (typeof value === "object")
        return (
            <dl className="space-y-2">
                {Object.entries(value).map(([key, v]) => (
                    <div key={key}>
                        <dt className="font-semibold">{key}</dt>
                        <dd className="ml-3 break-words">
                            <Evidence value={v} />
                        </dd>
                    </div>
                ))}
            </dl>
        );
    const url = safeUrl(value);
    return url ? (
        <a
            className="underline text-copper"
            href={url}
            target="_blank"
            rel="noreferrer"
        >
            {String(value)}
        </a>
    ) : (
        <span>{String(value)}</span>
    );
}
export default function CurationWorkspace({
    initialFilters = {},
}: {
    initialFilters?: Record<string, string>;
}) {
    const legacy =
        initialFilters.workflow &&
        initialFilters.workflow !== "podcast_association";
    const [view, setView] = useState(
        initialFilters.view === "relationships" ||
            initialFilters.workflow === "podcast_association"
            ? "relationships"
            : "intake",
    );
    const [kind, setKind] = useState(initialFilters.kind ?? "all"),
        [state, setState] = useState(initialFilters.state ?? "all"),
        [q, setQ] = useState(initialFilters.q ?? ""),
        [page, setPage] = useState(1);
    const [selected, setSelected] = useState<string | null>(
            initialFilters.id ?? null,
        ),
        [queue, setQueue] = useState<InboxPage>({ items: [], hasMore: false }),
        [item, setItem] = useState<InboxDetail | null>(null);
    const [recordId, setRecordId] = useState(initialFilters.recordId ?? ""),
        [endpointKind] = useState(initialFilters.endpointKind ?? "comedian");
    const [refresh, setRefresh] = useState(0),
        [skipped, setSkipped] = useState<string[]>([]),
        [busy, setBusy] = useState(false),
        [loading, setLoading] = useState(true),
        [error, setError] = useState(""),
        [notice, setNotice] = useState(""),
        [reason, setReason] = useState("");
    const [pending, setPending] = useState<Pending | null>(null),
        [sent, setSent] = useState(false),
        [receipt, setReceipt] = useState(""),
        [showQueue, setShowQueue] = useState(false),
        [showFilters, setShowFilters] = useState(false),
        [proposing, setProposing] = useState(false);
    const initialSelection = useRef<string | undefined>(initialFilters.id),
        heading = useRef<HTMLHeadingElement>(null);
    const previewRegion = useRef<HTMLElement>(null);
    useEffect(() => {
        if (pending) {
            previewRegion.current?.focus();
            previewRegion.current?.scrollIntoView?.({ block: "start" });
        }
    }, [pending]);
    useEffect(() => {
        try {
            const saved = sessionStorage.getItem(storageKey);
            if (saved) {
                const p = JSON.parse(saved);
                if (p.requestId && p.url && p.body) {
                    setPending(p);
                    setSent(true);
                    setReceipt("unknown");
                    setNotice(
                        "An interrupted decision is saved. Check its status or retry the same request.",
                    );
                }
            }
        } catch {
            /* storage unavailable */
        }
    }, []);
    useEffect(() => {
        if (legacy) return;
        const controller = new AbortController();
        setLoading(true);
        setError("");
        const timer = setTimeout(() => {
            const params = new URLSearchParams({
                view,
                kind,
                state,
                q,
                page: String(page),
                ...(recordId ? { recordId, endpointKind } : {}),
            });
            inboxRequest<InboxPage>(
                `/api/admin/curation/inbox?${params}`,
                undefined,
                controller.signal,
            )
                .then((result) => {
                    if (controller.signal.aborted) return;
                    setQueue(result);
                    if (initialSelection.current) {
                        setSelected(initialSelection.current);
                        initialSelection.current = undefined;
                    } else
                        setSelected((prev) =>
                            result.items.some((x) => x.target.id === prev)
                                ? prev
                                : (result.items.find(
                                      (x) => !skipped.includes(x.target.id),
                                  )?.target.id ?? null),
                        );
                })
                .catch((e) => {
                    if (!controller.signal.aborted) setError(e.message);
                })
                .finally(() => {
                    if (!controller.signal.aborted) setLoading(false);
                });
        }, 200);
        return () => {
            controller.abort();
            clearTimeout(timer);
        };
    }, [
        legacy,
        view,
        kind,
        state,
        q,
        page,
        recordId,
        endpointKind,
        refresh,
        skipped,
    ]);
    useEffect(() => {
        setItem(null);
        setReason("");
        if (!selected || legacy) return;
        const controller = new AbortController();
        inboxRequest<InboxDetail>(
            `/api/admin/curation/inbox?${new URLSearchParams({ view, id: selected })}`,
            undefined,
            controller.signal,
        )
            .then((x) => {
                if (!controller.signal.aborted) setItem(x);
            })
            .catch((e) => {
                if (!controller.signal.aborted) setError(e.message);
            });
        return () => controller.abort();
    }, [selected, view, refresh, legacy]);
    useEffect(() => {
        if (legacy) return;
        const params = new URLSearchParams({
            view,
            kind,
            state,
            ...(q ? { q } : {}),
            ...(selected ? { id: selected } : {}),
            ...(recordId ? { recordId, endpointKind } : {}),
        });
        window.history.replaceState(null, "", `/admin/reviews?${params}`);
    }, [legacy, view, kind, state, q, selected, recordId, endpointKind]);
    function next() {
        if (pending || busy || !selected) return;
        setSkipped((prev) => [...prev, selected]);
        setSelected(
            queue.items.find(
                (x) =>
                    x.target.id !== selected && !skipped.includes(x.target.id),
            )?.target.id ?? null,
        );
        heading.current?.focus();
    }
    useEffect(() => {
        if (legacy) return;
        const key = (e: KeyboardEvent) => {
            if (
                e.altKey ||
                e.ctrlKey ||
                e.metaKey ||
                (e.target instanceof HTMLElement &&
                    e.target.closest(
                        "input,textarea,select,button,a,[contenteditable]",
                    ))
            )
                return;
            if (e.key.toLowerCase() === "j") {
                e.preventDefault();
                next();
            }
        };
        window.addEventListener("keydown", key);
        return () => window.removeEventListener("keydown", key);
    });
    function clearPending() {
        setPending(null);
        setSent(false);
        setReceipt("");
        try {
            sessionStorage.removeItem(storageKey);
        } catch {}
    }
    function recover() {
        clearPending();
        setError("");
        setRefresh((n) => n + 1);
        setNotice(
            "Current state reloaded. Review the evidence and preview a new decision.",
        );
    }
    async function result(data: { status: string; error?: string }) {
        setReceipt(data.status);
        if (data.status === "applied") {
            clearPending();
            setNotice(
                "Decision applied. Review the updated state or advance to the next item.",
            );
            setRefresh((n) => n + 1);
        } else if (data.status === "pending")
            setNotice(
                "Submitted — waiting to be applied. This is not an approval yet.",
            );
        else
            setError(
                data.error ??
                    `Decision ${data.status}. Reload current state before deciding again.`,
            );
    }
    async function check() {
        if (!pending || busy) return;
        setBusy(true);
        setError("");
        try {
            await result(
                await inboxRequest(
                    `/api/admin/curation?requestId=${pending.requestId}`,
                ),
            );
        } catch (e) {
            setError((e as Error).message);
        } finally {
            setBusy(false);
        }
    }
    useEffect(() => {
        if (receipt !== "pending") return;
        const timer = setInterval(() => {
            void check();
        }, 5000);
        return () => clearInterval(timer);
    });
    async function submit() {
        if (!pending || busy) return;
        setBusy(true);
        setError("");
        setSent(true);
        setReceipt("unknown");
        try {
            sessionStorage.setItem(storageKey, JSON.stringify(pending));
        } catch {}
        try {
            await result(await inboxRequest(pending.url, pending.body));
        } catch (e) {
            const status = (e as Error & { status?: number }).status;
            setReceipt(status === 409 ? "conflict" : "unknown");
            setError((e as Error).message);
        } finally {
            setBusy(false);
        }
    }
    async function preview(action: InboxAction) {
        if (!item || busy || !reason.trim()) return;
        setBusy(true);
        setError("");
        const requestId = crypto.randomUUID();
        try {
            let url = "/api/admin/curation";
            let body: Record<string, unknown>;
            let p: InboxPreview;
            if (
                item.target.kind === "alias_of" &&
                (action === "confirm" || action === "sever")
            ) {
                url = "/api/admin/curation/parents";
                const input = {
                    childId: item.sourceRecordId,
                    parentId: action === "sever" ? null : item.targetRecordId,
                    reason: reason.trim(),
                    requestId,
                };
                p = await inboxRequest(url, { operation: "preview", ...input });
                body = {
                    operation: "submit",
                    ...input,
                    previewToken: p.previewToken,
                };
            } else {
                const command: Command = {
                    requestId,
                    target: item.target,
                    expectedVersion: item.version,
                    action,
                    reason: reason.trim(),
                };
                p = await inboxRequest(url, { operation: "preview", command });
                body = { operation: "submit", command };
            }
            setPending({
                url,
                body,
                requestId,
                preview: p,
                label: `${actionLabels[action]}: ${item.label}`,
            });
            setSent(false);
            setReceipt("");
        } catch (e) {
            setError((e as Error).message);
        } finally {
            setBusy(false);
        }
    }
    async function reconcile(id: string) {
        if (!reason.trim() || busy) return;
        setBusy(true);
        setError("");
        try {
            const preview = await inboxRequest<InboxPreview>(
                "/api/admin/curation/hosts",
                { operation: "previewReconciliation", input: { id } },
            );
            const requestId = crypto.randomUUID();
            setPending({
                url: "/api/admin/curation/hosts",
                body: {
                    operation: "reconcile",
                    input: {
                        id,
                        requestId,
                        token: preview.token,
                        reason: reason.trim(),
                    },
                },
                requestId,
                preview,
                label: "Reconcile canonical identity decisions",
            });
            setSent(false);
        } catch (e) {
            setError((e as Error).message);
        } finally {
            setBusy(false);
        }
    }
    const locked = busy || !!pending;
    function filters() {
        setSelected(null);
        setItem(null);
        setPage(1);
        setSkipped([]);
        initialSelection.current = undefined;
    }
    return (
        <div className="space-y-4 font-dmSans text-foreground">
            <nav aria-label="Review workflows" className="flex flex-wrap gap-2">
                {[
                    ["Intake", "/admin/reviews?view=intake"],
                    ["Relationships", "/admin/reviews?view=relationships"],
                    [
                        "Performer evidence",
                        "/admin/reviews?workflow=comedian_identity",
                    ],
                    [
                        "Event eligibility",
                        "/admin/reviews?workflow=event_eligibility",
                    ],
                    [
                        "Public visibility",
                        "/admin/reviews?workflow=comedian_visibility",
                    ],
                ].map(([label, url]) => (
                    <a
                        key={label}
                        className={button}
                        href={url}
                        onClick={(e) => {
                            if (locked) e.preventDefault();
                        }}
                        aria-disabled={locked}
                    >
                        {label}
                    </a>
                ))}
            </nav>
            {legacy && !pending ? (
                <ReviewWorkspace initialFilters={initialFilters} />
            ) : (
                <>
                    <p className="text-sm text-muted-foreground">
                        Intake decisions control what can enter again. Public
                        hide/show and relationship decisions are separate.
                        Restore always reopens review.
                    </p>
                    <button
                        className={`${button} lg:hidden`}
                        aria-expanded={showFilters}
                        onClick={() => setShowFilters((v) => !v)}
                    >
                        Queue filters
                    </button>
                    <fieldset
                        disabled={locked}
                        className={`${showFilters ? "grid" : "hidden"} gap-3 rounded-lg border border-strong bg-surface p-4 lg:grid lg:grid-cols-4`}
                    >
                        <label>
                            View
                            <select
                                className={field}
                                value={view}
                                onChange={(e) => {
                                    filters();
                                    setKind("all");
                                    setState("all");
                                    setView(e.target.value);
                                }}
                            >
                                <option value="intake">Intake</option>
                                <option value="relationships">
                                    Relationships
                                </option>
                            </select>
                        </label>
                        <label>
                            Type
                            <select
                                className={field}
                                value={kind}
                                onChange={(e) => {
                                    filters();
                                    setKind(e.target.value);
                                }}
                            >
                                {(view === "intake"
                                    ? [
                                          "all",
                                          "comedian",
                                          "club",
                                          "show",
                                          "podcast",
                                      ]
                                    : [
                                          "all",
                                          "alias_of",
                                          "host_of",
                                          "cohost_of",
                                      ]
                                ).map((k) => (
                                    <option key={k} value={k}>
                                        {kindLabels[k]}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label>
                            State
                            <select
                                className={field}
                                value={state}
                                onChange={(e) => {
                                    filters();
                                    setState(e.target.value);
                                }}
                            >
                                {(view === "intake"
                                    ? ["all", "pending", "approved", "blocked"]
                                    : [
                                          "all",
                                          "proposed",
                                          "confirmed",
                                          "rejected",
                                          "severed",
                                      ]
                                ).map((s) => (
                                    <option key={s} value={s}>
                                        {stateLabels[s]}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label>
                            Search names
                            <input
                                type="search"
                                className={field}
                                value={q}
                                onChange={(e) => {
                                    filters();
                                    setQ(e.target.value);
                                }}
                            />
                        </label>
                        {recordId && (
                            <button
                                className={button}
                                onClick={() => {
                                    filters();
                                    setRecordId("");
                                }}
                            >
                                Clear record filter ({recordId})
                            </button>
                        )}
                        <button
                            className={button}
                            onClick={() => {
                                setSkipped([]);
                                setRefresh((n) => n + 1);
                            }}
                        >
                            Refresh queue
                        </button>
                        {view === "relationships" && (
                            <button
                                className={button}
                                onClick={() => setProposing((v) => !v)}
                            >
                                Propose relationship
                            </button>
                        )}
                    </fieldset>
                    {proposing && (
                        <RelationshipProposal
                            disabled={locked}
                            onCreated={(id) => {
                                setProposing(false);
                                setSelected(id);
                                initialSelection.current = id;
                                setRefresh((n) => n + 1);
                            }}
                        />
                    )}
                    {notice && (
                        <p
                            role="status"
                            className="rounded border border-copper/40 p-3"
                        >
                            {notice}
                        </p>
                    )}
                    {error && (
                        <div
                            role="alert"
                            className="space-y-2 rounded border border-red-500 p-3"
                        >
                            <p>{error}</p>
                            <button
                                className={button}
                                disabled={
                                    busy ||
                                    receipt === "unknown" ||
                                    receipt === "pending"
                                }
                                onClick={recover}
                            >
                                Reload current state
                            </button>
                        </div>
                    )}
                    {pending && (
                        <section
                            aria-label="Decision preview"
                            ref={previewRegion}
                            tabIndex={-1}
                            className="space-y-3 rounded-lg border border-copper p-4"
                        >
                            <h2 className="font-bold">{pending.label}</h2>
                            <ul className="list-disc space-y-2 pl-5">
                                {pending.preview.effects.map((e, i) => (
                                    <li key={i} className="break-words">
                                        {e}
                                    </li>
                                ))}
                            </ul>
                            <p>{pending.preview.boundaries}</p>
                            <p>{pending.preview.restoration}</p>
                            <p>
                                Reason:{" "}
                                {String(
                                    (
                                        pending.body.command as
                                            | Command
                                            | undefined
                                    )?.reason ??
                                        pending.body.reason ??
                                        (
                                            pending.body.input as
                                                | { reason?: string }
                                                | undefined
                                        )?.reason,
                                )}
                            </p>
                            <p>{pending.preview.disabledReason}</p>
                            <div className="flex flex-wrap gap-2">
                                <button
                                    className={button}
                                    disabled={
                                        busy ||
                                        pending.preview.available === false ||
                                        receipt === "conflict" ||
                                        receipt === "failed"
                                    }
                                    onClick={() => void submit()}
                                >
                                    {sent
                                        ? "Retry same request"
                                        : "Apply decision"}
                                </button>
                                {sent &&
                                    pending.url !==
                                        "/api/admin/curation/hosts" && (
                                        <button
                                            className={button}
                                            disabled={busy}
                                            onClick={() => void check()}
                                        >
                                            Check request status
                                        </button>
                                    )}
                                {!sent && (
                                    <button
                                        className={button}
                                        disabled={busy}
                                        onClick={clearPending}
                                    >
                                        Edit decision
                                    </button>
                                )}
                                {["conflict", "failed", "canceled"].includes(
                                    receipt,
                                ) && (
                                    <button
                                        className={button}
                                        disabled={busy}
                                        onClick={recover}
                                    >
                                        Reload and review again
                                    </button>
                                )}
                            </div>
                            <p role="status">
                                {receipt === "pending"
                                    ? "Submitted, not yet applied."
                                    : receipt === "unknown"
                                      ? "Outcome not yet confirmed. Retry uses the same request ID."
                                      : receipt}
                            </p>
                        </section>
                    )}
                    <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(230px,1fr)_minmax(0,3fr)]">
                        <aside className="min-w-0 rounded-lg border border-strong bg-surface p-3">
                            <button
                                className={`${button} lg:hidden`}
                                aria-expanded={showQueue}
                                onClick={() => setShowQueue((v) => !v)}
                            >
                                Review queue ({queue.items.length})
                            </button>
                            <div
                                className={`${showQueue ? "block" : "hidden"} space-y-2 lg:block`}
                            >
                                <h2 className="font-bold">Review queue</h2>
                                {loading ? (
                                    <p role="status">Loading…</p>
                                ) : (
                                    queue.items
                                        .filter(
                                            (x) =>
                                                !skipped.includes(x.target.id),
                                        )
                                        .map((x) => (
                                            <button
                                                key={x.target.id}
                                                disabled={locked}
                                                className={`${button} block w-full text-left ${selected === x.target.id ? "border-copper bg-copper/10" : ""}`}
                                                onClick={() => {
                                                    setSelected(x.target.id);
                                                    setShowQueue(false);
                                                }}
                                                aria-pressed={
                                                    selected === x.target.id
                                                }
                                            >
                                                <span className="block break-words">
                                                    {x.label}
                                                </span>
                                                <span className="text-xs">
                                                    {kindLabels[x.target.kind]}{" "}
                                                    · {stateLabels[x.state]}
                                                </span>
                                            </button>
                                        ))
                                )}
                                {!loading && !queue.items.length && (
                                    <p>No matching reviews.</p>
                                )}
                                <div className="flex gap-2">
                                    <button
                                        className={button}
                                        disabled={locked || page === 1}
                                        onClick={() => {
                                            setSkipped([]);
                                            setPage((p) => p - 1);
                                        }}
                                    >
                                        Previous
                                    </button>
                                    <button
                                        className={button}
                                        disabled={locked || !queue.hasMore}
                                        onClick={() => {
                                            setSkipped([]);
                                            setPage((p) => p + 1);
                                        }}
                                    >
                                        Next page
                                    </button>
                                </div>
                            </div>
                        </aside>
                        <section
                            aria-label="Review detail"
                            className="min-w-0 space-y-4 rounded-lg border border-strong bg-surface p-4"
                        >
                            <h2
                                ref={heading}
                                tabIndex={-1}
                                className="break-words text-xl font-bold"
                            >
                                {item?.label ?? "Select a review"}
                            </h2>
                            {item && (
                                <>
                                    <p>
                                        {kindLabels[item.target.kind]} ·{" "}
                                        {stateLabels[item.state]}
                                    </p>
                                    {item.target.type === "relationship" ? (
                                        <p>
                                            From: {item.sourceLabel} → To:{" "}
                                            {item.targetLabel}. This decision
                                            changes only this relationship,
                                            never either entity’s intake
                                            approval.
                                        </p>
                                    ) : (
                                        <div className="space-y-2">
                                            <p>
                                                Rejection scope:{" "}
                                                <strong>
                                                    {item.target.scope ===
                                                    "name"
                                                        ? "Exact normalized name"
                                                        : item.target.scope ===
                                                            "series"
                                                          ? "Source-owned recurring series, including future occurrences"
                                                          : item.target.kind ===
                                                              "show"
                                                            ? "One occurrence and confirmed cross-source mappings"
                                                            : "This identity and its known identifiers"}
                                                </strong>
                                                .
                                            </p>
                                            <p className="text-sm">
                                                Blocking prevents future intake
                                                within this scope. It is not a
                                                temporary public hide. A show
                                                title alone never blocks an
                                                entire series.
                                            </p>
                                            {item.recordId &&
                                                ["comedian", "club"].includes(
                                                    item.target.kind,
                                                ) && (
                                                    <a
                                                        className="underline"
                                                        href={`/admin/reviews?workflow=${item.target.kind}_visibility&id=${item.recordId}`}
                                                    >
                                                        Review public hide/show
                                                        separately
                                                    </a>
                                                )}
                                        </div>
                                    )}
                                    {!!item.keys.length && (
                                        <details>
                                            <summary className="cursor-pointer font-semibold">
                                                Identifiers defining this scope
                                                ({item.keys.length})
                                            </summary>
                                            <Evidence value={item.keys} />
                                        </details>
                                    )}
                                    {!!item.matches.length && (
                                        <div>
                                            <h3 className="font-bold">
                                                Existing name matches — verify
                                                identity before linking
                                            </h3>
                                            {item.matches.map((m) => (
                                                <a
                                                    key={m.target.id}
                                                    className="block underline"
                                                    href={`/admin/reviews?view=intake&id=${encodeURIComponent(m.target.id)}`}
                                                >
                                                    {m.label} · {m.state} ·{" "}
                                                    {m.recordId ?? "staged"}
                                                </a>
                                            ))}
                                        </div>
                                    )}
                                    <div>
                                        <h3 className="font-bold">
                                            Source evidence
                                        </h3>
                                        {!item.observations.length ? (
                                            <p>
                                                No source evidence recorded.
                                                Approval may be unavailable.
                                            </p>
                                        ) : (
                                            item.observations.map((o) => (
                                                <details
                                                    key={o.id}
                                                    className="mt-2 rounded border border-strong p-3"
                                                >
                                                    <summary className="cursor-pointer break-words">
                                                        {o.source} ·{" "}
                                                        {o.source_key} ·{" "}
                                                        {new Date(
                                                            o.recorded_at,
                                                        ).toLocaleString()}
                                                    </summary>
                                                    <Evidence
                                                        value={o.evidence}
                                                    />
                                                </details>
                                            ))
                                        )}
                                        {item.observations.length === 100 && (
                                            <p>
                                                Showing the latest 100
                                                observations.
                                            </p>
                                        )}
                                    </div>
                                    {item.target.kind === "comedian" &&
                                        item.state === "pending" &&
                                        !item.candidateId && (
                                            <p>
                                                This identity has no performer
                                                candidate to validate yet. Keep
                                                it pending until source evidence
                                                is staged, or block intake.
                                            </p>
                                        )}
                                    {item.target.kind === "comedian" &&
                                        item.state === "pending" &&
                                        item.candidateId && (
                                            <a
                                                className={button}
                                                href={`/admin/reviews?workflow=comedian_identity&id=${encodeURIComponent(item.candidateId)}`}
                                            >
                                                Validate performer evidence and
                                                choose appearances
                                            </a>
                                        )}
                                    <label className="block">
                                        Decision reason
                                        <textarea
                                            maxLength={2000}
                                            className={field}
                                            value={reason}
                                            disabled={locked}
                                            onChange={(e) =>
                                                setReason(e.target.value)
                                            }
                                        />
                                    </label>
                                    <div className="flex flex-wrap gap-2">
                                        {availableActions(item).map(
                                            (action) => (
                                                <button
                                                    key={action}
                                                    className={button}
                                                    disabled={
                                                        locked || !reason.trim()
                                                    }
                                                    onClick={() =>
                                                        void preview(action)
                                                    }
                                                >
                                                    {actionLabels[action]}
                                                </button>
                                            ),
                                        )}
                                        <button
                                            className={button}
                                            disabled={locked}
                                            onClick={next}
                                        >
                                            Skip / next
                                        </button>
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        Skip makes no decision. Press J outside
                                        a field to advance. Every change
                                        requires a preview.
                                    </p>
                                    {!!item.reconciliations.length && (
                                        <div>
                                            <h3 className="font-bold">
                                                Canonical identity
                                                reconciliation
                                            </h3>
                                            {item.reconciliations.map((h) => (
                                                <div
                                                    key={h.id}
                                                    className="mt-2 border border-strong p-3"
                                                >
                                                    {h.resolved_at ? (
                                                        <p>
                                                            Reviewed by{" "}
                                                            {h.actor}:{" "}
                                                            {h.reason}
                                                        </p>
                                                    ) : (
                                                        <>
                                                            <p>
                                                                Attribution is
                                                                on hold until
                                                                both identity
                                                                decisions are
                                                                reviewed.
                                                            </p>
                                                            <button
                                                                className={
                                                                    button
                                                                }
                                                                disabled={
                                                                    locked ||
                                                                    !reason.trim()
                                                                }
                                                                onClick={() =>
                                                                    void reconcile(
                                                                        h.id,
                                                                    )
                                                                }
                                                            >
                                                                Preview
                                                                reconciliation
                                                            </button>
                                                        </>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    <details open>
                                        <summary className="cursor-pointer font-bold">
                                            Decision history (
                                            {item.decisions.length})
                                        </summary>
                                        <ol className="mt-2 space-y-3">
                                            {item.decisions.map((d) => (
                                                <li
                                                    key={d.id}
                                                    className="border-l-2 border-copper/40 pl-3"
                                                >
                                                    <strong>
                                                        {d.action}:{" "}
                                                        {d.before_state} →{" "}
                                                        {d.after_state}
                                                    </strong>
                                                    <p>{d.reason}</p>
                                                    <p>
                                                        {d.actor} ·{" "}
                                                        {new Date(
                                                            d.created_at,
                                                        ).toLocaleString()}
                                                    </p>
                                                </li>
                                            ))}
                                        </ol>
                                    </details>
                                    {!!item.requests.length && (
                                        <details>
                                            <summary>
                                                Processing history (
                                                {item.requests.length})
                                            </summary>
                                            {item.requests.map((r) => (
                                                <p key={r.id}>
                                                    {r.action} · {r.status} ·{" "}
                                                    {r.actor} · {r.reason}{" "}
                                                    {r.error}
                                                </p>
                                            ))}
                                        </details>
                                    )}
                                </>
                            )}
                        </section>
                    </div>
                </>
            )}
        </div>
    );
}
