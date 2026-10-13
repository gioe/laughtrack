"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
    Check,
    ChevronDown,
    ExternalLink,
    Link2,
    RefreshCw,
    Undo2,
    X,
} from "lucide-react";
import { adminRequest } from "../shared/adminRequest";
import { AdminSearchField, AdminSelectField } from "../shared/AdminControls";
import {
    workflowLabels,
    type ReviewItem,
    type ReviewPage,
    type ReviewStatus,
    type ReviewWorkflow,
} from "@/lib/admin/reviewTypes";
const button =
    "rounded-md border border-strong px-3 py-2 font-semibold hover:bg-surface-elevated focus-visible:outline focus-visible:outline-2 focus-visible:outline-copper disabled:opacity-40";
const field =
    "w-full rounded-md border border-input bg-background px-3 py-2 text-foreground focus:border-copper focus:outline-none focus:ring-2 focus:ring-copper/30";
function sourceUrl(value: string | null) {
    try {
        const u = new URL(value ?? "");
        return ["http:", "https:"].includes(u.protocol) ? u.href : null;
    } catch {
        return null;
    }
}
export default function ReviewWorkspace() {
    const [workflow, setWorkflow] =
        useState<ReviewWorkflow>("comedian_identity");
    const [status, setStatus] = useState<ReviewStatus>("pending");
    const [q, setQ] = useState("");
    const [page, setPage] = useState(1);
    const [queue, setQueue] = useState<ReviewPage>({
        items: [],
        total: 0,
        page: 1,
    });
    const [selected, setSelected] = useState<string | null>(null);
    const [item, setItem] = useState<ReviewItem | null>(null);
    const [loading, setLoading] = useState(true);
    const [showQueue, setShowQueue] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const [notice, setNotice] = useState("");
    const [undoId, setUndoId] = useState<string | null>(null);
    const [refresh, setRefresh] = useState(0);
    const [skipped, setSkipped] = useState<string[]>([]);
    const [name, setName] = useState("");
    const [reason, setReason] = useState("");
    const [matchQuery, setMatchQuery] = useState("");
    const [matches, setMatches] = useState<{ id: number; name: string }[]>([]);
    const [target, setTarget] = useState<number | null>(null);
    const [showIds, setShowIds] = useState<number[]>([]);
    const generation = useRef(0);
    const detailRef = useRef<HTMLHeadingElement>(null);
    useEffect(() => {
        const controller = new AbortController();
        const n = ++generation.current;
        setLoading(true);
        setError("");
        const timer = setTimeout(() => {
            const params = new URLSearchParams({
                workflow,
                status,
                q,
                page: String(page),
            });
            adminRequest<ReviewPage>(`/api/admin/reviews?${params}`, {
                signal: controller.signal,
            })
                .then((result) => {
                    if (n !== generation.current) return;
                    setQueue(result);
                    if (result.items.length === 0 && page > 1)
                        setPage(page - 1);
                    setSelected((prev) =>
                        result.items.some((x) => x.id === prev)
                            ? prev
                            : (result.items.find((x) => !skipped.includes(x.id))
                                  ?.id ?? null),
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
    }, [workflow, status, q, page, refresh, skipped]);
    useEffect(() => {
        setItem(null);
        setTarget(null);
        setShowIds([]);
        setReason("");
        setMatchQuery("");
        setMatches([]);
        if (!selected) return;
        const controller = new AbortController();
        adminRequest<ReviewItem>(
            `/api/admin/reviews?${new URLSearchParams({ workflow, id: selected })}`,
            { signal: controller.signal },
        )
            .then((result) => {
                setItem(result);
                setName(result.title);
                setMatches(result.matches);
            })
            .catch((e) => {
                if (!controller.signal.aborted) setError(e.message);
            });
        return () => controller.abort();
    }, [workflow, selected, refresh]);
    useEffect(() => {
        if (workflow !== "comedian_identity" || !matchQuery.trim()) return;
        const controller = new AbortController();
        const timer = setTimeout(() => {
            adminRequest<{ id: number; name: string }[]>(
                `/api/admin/reviews?search=${encodeURIComponent(matchQuery)}`,
                { signal: controller.signal },
            )
                .then(setMatches)
                .catch((e) => {
                    if (!controller.signal.aborted) setError(e.message);
                });
        }, 250);
        return () => {
            controller.abort();
            clearTimeout(timer);
        };
    }, [matchQuery, workflow]);
    const next = useCallback(() => {
        if (!selected) return;
        const remaining = queue.items.filter(
            (x) => x.id !== selected && !skipped.includes(x.id),
        );
        setSkipped((prev) => [...prev, selected]);
        setSelected(remaining[0]?.id ?? null);
        detailRef.current?.focus();
    }, [selected, queue.items, skipped]);
    const decide = useCallback(
        async (action: "approve" | "link" | "reject") => {
            if (!item || busy) return;
            setBusy(true);
            setError("");
            try {
                const result = await adminRequest<{ decisionId: string }>(
                    "/api/admin/reviews",
                    {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            workflow,
                            id: item.id,
                            token: item.token,
                            action,
                            ...(workflow === "comedian_identity"
                                ? {
                                      name,
                                      targetId: target ?? undefined,
                                      showIds,
                                  }
                                : {}),
                            reason:
                                reason.trim() ||
                                (action === "reject"
                                    ? "Not supported by source evidence"
                                    : "Reviewed source evidence"),
                        }),
                    },
                );
                setUndoId(result.decisionId);
                setNotice(
                    `${item.title}: ${action === "reject" ? "rejected" : action === "link" ? "linked and validated" : "approved"}.`,
                );
                next();
                setRefresh((v) => v + 1);
            } catch (e) {
                setError(
                    e instanceof Error ? e.message : "Could not save decision.",
                );
            } finally {
                setBusy(false);
            }
        },
        [item, busy, workflow, name, target, showIds, reason, next],
    );
    useEffect(() => {
        const onKey = (event: KeyboardEvent) => {
            if (event.altKey || event.ctrlKey || event.metaKey || busy) return;
            if (
                event.target instanceof HTMLElement &&
                (event.target.closest("input,textarea,select,button,a") ||
                    event.target.isContentEditable)
            )
                return;
            if (event.key.toLowerCase() === "j") {
                event.preventDefault();
                next();
            }
            // Destructive decisions intentionally require the visible buttons.
        };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [busy, next]);
    async function undo() {
        if (!undoId || busy) return;
        setBusy(true);
        setError("");
        try {
            const restored = await adminRequest<{
                workflow: ReviewWorkflow;
                id: string;
            }>("/api/admin/reviews", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "undo", decisionId: undoId }),
            });
            setUndoId(null);
            setNotice("Decision undone. The item is ready to review again.");
            setWorkflow(restored.workflow);
            setStatus("pending");
            setQ("");
            setPage(1);
            setSkipped([]);
            setSelected(restored.id);
            setRefresh((v) => v + 1);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Could not undo.");
        } finally {
            setBusy(false);
        }
    }
    const changeFilter = () => {
        setPage(1);
        setSkipped([]);
        setSelected(null);
        setItem(null);
    };
    return (
        <div className="space-y-4 font-dmSans text-foreground">
            <fieldset
                disabled={busy}
                className="grid gap-3 rounded-lg border border-strong bg-surface p-4 lg:grid-cols-[1fr_1fr_2fr_auto] lg:items-end"
            >
                <AdminSelectField
                    label="Review type"
                    value={workflow}
                    options={Object.entries(workflowLabels).map(
                        ([value, label]) => ({
                            value: value as ReviewWorkflow,
                            label,
                        }),
                    )}
                    onChange={(v) => {
                        changeFilter();
                        setWorkflow(v);
                    }}
                />
                <AdminSelectField
                    label="Status"
                    value={status}
                    options={[
                        { value: "pending", label: "Needs review" },
                        { value: "accepted", label: "Approved" },
                        { value: "rejected", label: "Rejected" },
                    ]}
                    onChange={(v) => {
                        changeFilter();
                        setStatus(v);
                    }}
                />
                <AdminSearchField
                    label="Search queue"
                    value={q}
                    placeholder="Search names or podcasts"
                    onChange={(v) => {
                        changeFilter();
                        setQ(v);
                    }}
                />
                <button
                    className={button}
                    disabled={busy}
                    onClick={() => setRefresh((v) => v + 1)}
                    aria-label="Refresh reviews"
                >
                    <RefreshCw size={18} />
                </button>
            </fieldset>
            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                <span>Other review workflows:</span>
                <Link
                    className="text-copper underline"
                    href="/admin/event-reviews"
                >
                    Show eligibility
                </Link>
                <Link className="text-copper underline" href="/admin/clubs">
                    Club management
                </Link>
            </div>
            {error && (
                <div
                    role="alert"
                    className="rounded-lg border border-red-400/40 bg-surface p-4 text-red-300"
                >
                    {error}{" "}
                    <button
                        className="ml-2 underline"
                        onClick={() => setRefresh((v) => v + 1)}
                    >
                        Refresh item
                    </button>
                </div>
            )}
            <div
                aria-live="polite"
                className="flex min-h-8 items-center gap-3 text-sm"
            >
                {notice}
                {undoId && (
                    <button
                        className="flex items-center gap-1 text-copper underline"
                        disabled={busy}
                        onClick={undo}
                    >
                        <Undo2 size={16} />
                        Undo last decision
                    </button>
                )}
            </div>
            <div className="grid min-h-[560px] overflow-hidden rounded-lg border border-strong bg-surface lg:grid-cols-[320px_minmax(0,1fr)]">
                <aside
                    className="border-b border-strong lg:border-b-0 lg:border-r"
                    aria-label="Review queue"
                >
                    <div className="flex items-center justify-between border-b border-strong p-4">
                        <strong>
                            {queue.total}{" "}
                            {status === "pending" ? "to review" : status}
                        </strong>
                        {loading && <span role="status">Loading…</span>}
                    </div>
                    <button
                        className={`${button} m-3 lg:hidden`}
                        onClick={() => setShowQueue((v) => !v)}
                    >
                        {showQueue ? "Close queue" : "Browse queue"}
                    </button>
                    <div className={showQueue ? "" : "hidden lg:block"}>
                        <div className="max-h-[640px] overflow-y-auto">
                            {queue.items
                                .filter((x) => !skipped.includes(x.id))
                                .map((x) => (
                                    <button
                                        key={x.id}
                                        disabled={busy || loading}
                                        onClick={() => {
                                            setSelected(x.id);
                                            setShowQueue(false);
                                        }}
                                        aria-current={
                                            x.id === selected
                                                ? "true"
                                                : undefined
                                        }
                                        className={`block w-full border-b border-strong p-4 text-left focus-visible:outline focus-visible:outline-copper ${x.id === selected ? "border-l-4 border-l-copper bg-surface-elevated" : "hover:bg-surface-elevated"}`}
                                    >
                                        <span className="block break-words font-semibold">
                                            {x.title}
                                        </span>
                                        <span className="mt-1 block text-sm text-muted-foreground">
                                            {x.subtitle}
                                        </span>
                                    </button>
                                ))}
                            {!loading && !queue.items.length && (
                                <p className="p-6 text-muted-foreground">
                                    {q
                                        ? "No matching reviews."
                                        : "You're all caught up in this queue."}
                                </p>
                            )}
                        </div>
                        <div className="flex items-center justify-between gap-2 p-3">
                            <button
                                className={button}
                                disabled={page === 1 || busy}
                                onClick={() => {
                                    setPage((v) => v - 1);
                                    setSkipped([]);
                                }}
                            >
                                Previous
                            </button>
                            <span className="text-sm">
                                {page} /{" "}
                                {Math.max(1, Math.ceil(queue.total / 30))}
                            </span>
                            <button
                                className={button}
                                disabled={page * 30 >= queue.total || busy}
                                onClick={() => {
                                    setPage((v) => v + 1);
                                    setSkipped([]);
                                }}
                            >
                                Next
                            </button>
                        </div>
                        {skipped.length > 0 && (
                            <button
                                className="px-4 pb-4 text-sm text-copper underline"
                                onClick={() => setSkipped([])}
                            >
                                Return to skipped items ({skipped.length})
                            </button>
                        )}
                    </div>
                </aside>
                <section className="min-w-0 p-5 lg:p-6" aria-busy={busy}>
                    {!item ? (
                        <div className="flex min-h-80 items-center justify-center text-muted-foreground">
                            {selected
                                ? "Loading source evidence…"
                                : "Select an item to review."}
                        </div>
                    ) : (
                        <div className="space-y-6">
                            <header>
                                <p className="text-sm font-semibold uppercase text-copper">
                                    {workflowLabels[item.workflow]} ·{" "}
                                    {item.status}
                                </p>
                                <h2
                                    ref={detailRef}
                                    tabIndex={-1}
                                    className="mt-2 break-words font-chivo text-2xl font-bold"
                                >
                                    {item.title}
                                </h2>
                                <p className="mt-2 text-muted-foreground">
                                    {item.subtitle}
                                </p>
                            </header>
                            {workflow === "comedian_identity" &&
                                item.status === "pending" && (
                                    <div className="grid gap-4">
                                        <label className="grid gap-1 font-semibold">
                                            Proposed name
                                            <input
                                                className={field}
                                                value={name}
                                                disabled={busy}
                                                onChange={(e) =>
                                                    setName(e.target.value)
                                                }
                                            />
                                        </label>
                                        <div>
                                            <label className="grid gap-1 font-semibold">
                                                Match an existing comedian
                                                <input
                                                    type="search"
                                                    className={field}
                                                    placeholder="Search canonical names"
                                                    value={matchQuery}
                                                    disabled={busy}
                                                    onChange={(e) => {
                                                        setMatchQuery(
                                                            e.target.value,
                                                        );
                                                        setTarget(null);
                                                    }}
                                                />
                                            </label>
                                            <div className="mt-2 flex flex-wrap gap-2">
                                                {matches.map((m) => (
                                                    <button
                                                        key={m.id}
                                                        aria-pressed={
                                                            target === m.id
                                                        }
                                                        className={`${button} ${target === m.id ? "border-copper bg-copper-dark text-white" : ""}`}
                                                        disabled={busy}
                                                        onClick={() =>
                                                            setTarget(
                                                                target === m.id
                                                                    ? null
                                                                    : m.id,
                                                            )
                                                        }
                                                    >
                                                        {m.name}
                                                    </button>
                                                ))}
                                            </div>
                                            <p className="mt-2 text-sm text-muted-foreground">
                                                {target
                                                    ? "This existing profile will be validated; no duplicate profile will be created."
                                                    : "Check for a match before creating a new profile."}
                                            </p>
                                        </div>
                                    </div>
                                )}
                            <div>
                                <h3 className="mb-3 font-semibold">
                                    Source evidence
                                </h3>
                                <div className="max-h-[480px] space-y-3 overflow-y-auto pr-1">
                                    {item.evidence.length === 0 && (
                                        <p className="text-muted-foreground">
                                            No source evidence recorded. Leave
                                            this pending until you can verify
                                            it.
                                        </p>
                                    )}
                                    {item.evidence.map((e) => (
                                        <article
                                            key={e.id}
                                            className="rounded-lg border border-strong bg-canvas p-4"
                                        >
                                            <div className="flex items-start justify-between gap-3">
                                                <div>
                                                    <p className="break-words font-semibold">
                                                        {e.title}
                                                    </p>
                                                    <p className="mt-1 text-sm text-muted-foreground">
                                                        {e.source} ·{" "}
                                                        {e.kind.replaceAll(
                                                            "_",
                                                            " ",
                                                        )}
                                                        {e.date
                                                            ? ` · ${new Date(e.date).toLocaleDateString()}`
                                                            : ""}
                                                    </p>
                                                </div>
                                                {sourceUrl(e.url) && (
                                                    <a
                                                        href={sourceUrl(e.url)!}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="shrink-0 text-copper"
                                                        aria-label={`Open source for ${e.title}`}
                                                    >
                                                        <ExternalLink
                                                            size={18}
                                                        />
                                                    </a>
                                                )}
                                            </div>
                                            <p className="mt-3 whitespace-pre-wrap break-words text-sm text-muted-foreground">
                                                {e.context.replace(
                                                    /<[^>]*>/g,
                                                    " ",
                                                )}
                                            </p>
                                            {e.showId &&
                                                item.status === "pending" && (
                                                    <label className="mt-3 flex items-center gap-2 text-sm">
                                                        <input
                                                            type="checkbox"
                                                            disabled={busy}
                                                            checked={showIds.includes(
                                                                e.showId,
                                                            )}
                                                            onChange={(ev) =>
                                                                setShowIds(
                                                                    (prev) =>
                                                                        ev
                                                                            .target
                                                                            .checked
                                                                            ? [
                                                                                  ...new Set(
                                                                                      [
                                                                                          ...prev,
                                                                                          e.showId!,
                                                                                      ],
                                                                                  ),
                                                                              ]
                                                                            : prev.filter(
                                                                                  (
                                                                                      id,
                                                                                  ) =>
                                                                                      id !==
                                                                                      e.showId,
                                                                              ),
                                                                )
                                                            }
                                                        />
                                                        Also confirm this show
                                                        appearance
                                                    </label>
                                                )}
                                        </article>
                                    ))}
                                </div>
                            </div>
                            {item.status === "pending" && (
                                <div className="sticky bottom-0 space-y-3 border-t border-strong bg-surface pt-4">
                                    <label className="grid gap-1 text-sm font-semibold">
                                        Decision note{" "}
                                        <span className="font-normal text-muted-foreground">
                                            Optional — add context for future
                                            reviews
                                        </span>
                                        <input
                                            className={field}
                                            value={reason}
                                            disabled={busy}
                                            placeholder="Why is this supported or not supported?"
                                            onChange={(e) =>
                                                setReason(e.target.value)
                                            }
                                        />
                                    </label>
                                    <div className="flex flex-wrap gap-2">
                                        <button
                                            className={`${button} flex items-center gap-2 border-copper bg-copper-dark text-white`}
                                            disabled={
                                                busy ||
                                                !name.trim() ||
                                                (workflow ===
                                                    "comedian_identity" &&
                                                    target !== null)
                                            }
                                            onClick={() => decide("approve")}
                                        >
                                            <Check size={18} />
                                            {workflow === "comedian_identity"
                                                ? "Approve new"
                                                : "Approve relationship"}
                                        </button>
                                        {workflow === "comedian_identity" && (
                                            <button
                                                className={`${button} flex items-center gap-2`}
                                                disabled={busy || !target}
                                                onClick={() => decide("link")}
                                            >
                                                <Link2 size={18} />
                                                Link existing
                                            </button>
                                        )}
                                        <button
                                            className={`${button} flex items-center gap-2`}
                                            disabled={busy}
                                            onClick={() => decide("reject")}
                                        >
                                            <X size={18} />
                                            Reject
                                        </button>
                                        <button
                                            className={`${button} ml-auto flex items-center gap-2`}
                                            disabled={busy}
                                            onClick={next}
                                        >
                                            Skip <ChevronDown size={16} />
                                        </button>
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        Skip keeps the item pending. Press J
                                        outside a field to skip.
                                    </p>
                                </div>
                            )}
                            {item.history.length > 0 && (
                                <details>
                                    <summary className="cursor-pointer font-semibold">
                                        Decision history ({item.history.length})
                                    </summary>
                                    <ol className="mt-3 space-y-3">
                                        {item.history.map((h) => (
                                            <li
                                                key={h.id}
                                                className="border-l-2 border-strong pl-3 text-sm"
                                            >
                                                <strong>
                                                    {h.action}
                                                    {h.undone
                                                        ? " · undone"
                                                        : ""}
                                                </strong>
                                                <p>{h.reason}</p>
                                                <p className="text-muted-foreground">
                                                    {new Date(
                                                        h.createdAt,
                                                    ).toLocaleString()}{" "}
                                                    · {h.actor}
                                                </p>
                                            </li>
                                        ))}
                                    </ol>
                                </details>
                            )}
                        </div>
                    )}
                </section>
            </div>
        </div>
    );
}
