"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ExternalLink, RefreshCw, Undo2 } from "lucide-react";
import { adminRequest } from "../shared/adminRequest";
import { AdminSearchField, AdminSelectField } from "../shared/AdminControls";
import {
    workflowLabels,
    reviewDefinitions,
    type ReviewAction,
    type ReviewResult,
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
export default function ReviewWorkspace({
    initialFilters = {},
}: {
    initialFilters?: Record<string, string>;
}) {
    const initialWorkflow = Object.hasOwn(
        reviewDefinitions,
        initialFilters.workflow ?? "",
    )
        ? (initialFilters.workflow as ReviewWorkflow)
        : "comedian_identity";
    const [workflow, setWorkflow] = useState<ReviewWorkflow>(initialWorkflow);
    const definition = reviewDefinitions[workflow];
    const [status, setStatus] = useState<ReviewStatus>(
        reviewDefinitions[initialWorkflow].statuses.some(
            (s) => s.value === initialFilters.status,
        )
            ? (initialFilters.status as ReviewStatus)
            : reviewDefinitions[initialWorkflow].defaultStatus,
    );
    const [q, setQ] = useState(initialFilters.q ?? "");
    const [source, setSource] = useState(initialFilters.source ?? "");
    const [mode, setMode] = useState(initialFilters.mode ?? "");
    const [cursors, setCursors] = useState([Number(initialFilters.after) || 0]);
    const [ceiling, setCeiling] = useState<number | undefined>(
        Number(initialFilters.ceiling) || undefined,
    );
    const [confirmation, setConfirmation] = useState<ReviewAction | null>(null);
    const requestIdentity = useRef<{ key: string; id: string } | null>(null);
    const [page, setPage] = useState(1);
    const [queue, setQueue] = useState<ReviewPage>({
        items: [],
        total: 0,
        page: 1,
    });
    const [selected, setSelected] = useState<string | null>(
        initialFilters.id ?? null,
    );
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
    const initialSelection = useRef<string | undefined>(initialFilters.id);
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
            if (definition.sourceFilters) {
                if (source) params.set("source", source);
                if (mode) params.set("mode", mode);
                params.set("after", String(cursors[page - 1] ?? 0));
                if (ceiling !== undefined)
                    params.set("ceiling", String(ceiling));
            }
            adminRequest<ReviewPage>(`/api/admin/reviews?${params}`, {
                signal: controller.signal,
            })
                .then((result) => {
                    if (controller.signal.aborted || n !== generation.current)
                        return;
                    setQueue(result);
                    if (result.items.length === 0 && page > 1)
                        setPage(page - 1);
                    if (initialSelection.current) {
                        setSelected(initialSelection.current);
                        initialSelection.current = undefined;
                        return;
                    }
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
    }, [
        workflow,
        status,
        q,
        page,
        refresh,
        skipped,
        source,
        mode,
        cursors,
        ceiling,
        definition.sourceFilters,
    ]);
    useEffect(() => {
        setItem(null);
        setConfirmation(null);
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
                if (controller.signal.aborted) return;
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
        if (!definition.identityFields || !matchQuery.trim()) return;
        const controller = new AbortController();
        const timer = setTimeout(() => {
            adminRequest<{ id: number; name: string }[]>(
                `/api/admin/reviews?search=${encodeURIComponent(matchQuery)}`,
                { signal: controller.signal },
            )
                .then((result) => {
                    if (!controller.signal.aborted) setMatches(result);
                })
                .catch((e) => {
                    if (!controller.signal.aborted) setError(e.message);
                });
        }, 250);
        return () => {
            controller.abort();
            clearTimeout(timer);
        };
    }, [matchQuery, workflow, definition.identityFields]);
    const next = useCallback(() => {
        if (!selected) return;
        const remaining = queue.items.filter(
            (x) => x.id !== selected && !skipped.includes(x.id),
        );
        setSkipped((prev) => [...prev, selected]);
        setSelected(remaining[0]?.id ?? null);
        detailRef.current?.focus();
    }, [selected, queue.items, skipped]);
    const actions =
        item?.actions ??
        (item?.status === "pending"
            ? definition.actions.map((a) => a.value)
            : []);
    useEffect(() => {
        if (!item?.processing) return;
        const timer = setInterval(() => setRefresh((v) => v + 1), 30000);
        return () => clearInterval(timer);
    }, [item?.processing]);
    const decide = async (action: ReviewAction, confirmed = false) => {
        if (
            !item ||
            busy ||
            item.workflow !== workflow ||
            !actions.includes(action)
        )
            return;
        if (definition.reasonRequired && !reason.trim()) return;
        if (definition.queued && !confirmed) {
            setConfirmation(action);
            return;
        }
        setBusy(true);
        setError("");
        const payload = {
            workflow,
            id: item.id,
            token: item.token,
            action,
            ...(definition.identityFields
                ? { name, targetId: target ?? undefined, showIds }
                : {}),
            reason:
                reason.trim() ||
                (action === "reject"
                    ? "Not supported by source evidence"
                    : "Reviewed source evidence"),
        };
        const key = JSON.stringify(payload);
        if (definition.queued && requestIdentity.current?.key !== key)
            requestIdentity.current = { key, id: crypto.randomUUID() };
        try {
            const result = await adminRequest<ReviewResult>(
                "/api/admin/reviews",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        ...payload,
                        ...(definition.queued
                            ? { requestId: requestIdentity.current!.id }
                            : {}),
                    }),
                },
            );
            setUndoId(result.decisionId ?? null);
            setNotice(
                result.notice ??
                    `${item.title}: ${action === "reject" ? "rejected" : action === "link" ? "linked and validated" : "approved"}.`,
            );
            setConfirmation(null);
            next();
            setRefresh((v) => v + 1);
        } catch (e) {
            setError(
                e instanceof Error ? e.message : "Could not save decision.",
            );
        } finally {
            setBusy(false);
        }
    };
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
            setSource("");
            setMode("");
            setCursors([0]);
            setCeiling(undefined);
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
        initialSelection.current = undefined;
        setPage(1);
        setCursors([0]);
        setCeiling(undefined);
        setConfirmation(null);
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
                        setStatus(reviewDefinitions[v].defaultStatus);
                        setSource("");
                        setMode("");
                    }}
                />
                <AdminSelectField
                    label="Status"
                    value={status}
                    options={definition.statuses}
                    onChange={(v) => {
                        changeFilter();
                        setStatus(v);
                    }}
                />
                <AdminSearchField
                    label="Search queue"
                    value={q}
                    placeholder="Search names, events or venues"
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
            {definition.sourceFilters && (
                <fieldset
                    disabled={busy}
                    className="flex flex-wrap items-end gap-3 rounded-lg border border-strong bg-surface p-4"
                >
                    <label className="grid gap-1 font-semibold">
                        Source ID
                        <input
                            className={field}
                            type="number"
                            min="1"
                            value={source}
                            onChange={(e) => {
                                changeFilter();
                                setSource(e.target.value);
                            }}
                        />
                    </label>
                    <AdminSelectField
                        label="Screening mode"
                        value={mode}
                        options={[
                            { value: "", label: "All modes" },
                            { value: "off", label: "Off" },
                            { value: "shadow", label: "Shadow" },
                            { value: "enforce", label: "Enforce" },
                        ]}
                        onChange={(v) => {
                            changeFilter();
                            setMode(v);
                        }}
                    />
                    <p className="text-sm text-muted-foreground">
                        Each event occurrence is reviewed separately.
                    </p>
                </fieldset>
            )}
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
                            {queue.total === null
                                ? `${queue.items.length} on this page`
                                : `${queue.total} ${definition.statuses.find((s) => s.value === status)?.label ?? status}`}
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
                                disabled={page === 1 || busy || loading}
                                onClick={() => {
                                    setPage((v) => v - 1);
                                    setSkipped([]);
                                }}
                            >
                                Previous
                            </button>
                            <span className="text-sm">
                                {queue.total === null
                                    ? `Page ${page}`
                                    : `${page} / ${Math.max(1, Math.ceil(queue.total / 30))}`}
                            </span>
                            <button
                                className={button}
                                disabled={
                                    busy ||
                                    loading ||
                                    (queue.cursor
                                        ? queue.cursor.next === null
                                        : page * 30 >= (queue.total ?? 0))
                                }
                                onClick={() => {
                                    if (queue.cursor) {
                                        setCursors((prev) => [
                                            ...prev.slice(0, page),
                                            queue.cursor!.next!,
                                        ]);
                                        setCeiling(queue.cursor.ceiling);
                                    }
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
                                    {definition.statuses.find(
                                        (s) => s.value === item.status,
                                    )?.label ?? item.status}
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
                            {item.notice && (
                                <p
                                    role="status"
                                    className="rounded-lg border border-strong bg-surface-elevated p-3 text-sm"
                                >
                                    {item.notice}
                                </p>
                            )}
                            {definition.identityFields &&
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
                            {actions.length > 0 && (
                                <div className="sticky bottom-0 space-y-3 border-t border-strong bg-surface pt-4">
                                    <label className="grid gap-1 text-sm font-semibold">
                                        Decision note{" "}
                                        <span className="font-normal text-muted-foreground">
                                            {definition.reasonRequired
                                                ? "Required — explain the evidence for this decision"
                                                : "Optional — add context for future reviews"}
                                        </span>
                                        <input
                                            className={field}
                                            value={reason}
                                            maxLength={2000}
                                            required={definition.reasonRequired}
                                            disabled={
                                                busy || confirmation !== null
                                            }
                                            placeholder="Why is this supported or not supported?"
                                            onChange={(e) =>
                                                setReason(e.target.value)
                                            }
                                        />
                                    </label>
                                    {confirmation ? (
                                        <div
                                            className="space-y-3 rounded-md border border-copper p-4"
                                            aria-label="Confirm review"
                                        >
                                            <h3 className="font-semibold">
                                                Confirm {confirmation} for this
                                                occurrence
                                            </h3>
                                            <p>
                                                {item.title} · {item.subtitle}
                                            </p>
                                            <p>{reason}</p>
                                            <p className="text-sm text-muted-foreground">
                                                The worker rechecks the evidence
                                                before applying this decision.
                                            </p>
                                            <button
                                                className={button}
                                                disabled={busy}
                                                onClick={() =>
                                                    decide(confirmation, true)
                                                }
                                            >
                                                Confirm review
                                            </button>{" "}
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
                                    ) : (
                                        <div className="flex flex-wrap gap-2">
                                            {definition.actions
                                                .filter((a) =>
                                                    actions.includes(a.value),
                                                )
                                                .map((a) => (
                                                    <button
                                                        key={a.value}
                                                        className={`${button} ${a.value === "approve" ? "border-copper bg-copper-dark text-white" : ""}`}
                                                        disabled={
                                                            busy ||
                                                            (definition.reasonRequired &&
                                                                !reason.trim()) ||
                                                            (definition.identityFields &&
                                                                ((a.value ===
                                                                    "approve" &&
                                                                    (!name.trim() ||
                                                                        target !==
                                                                            null)) ||
                                                                    (a.value ===
                                                                        "link" &&
                                                                        !target)))
                                                        }
                                                        onClick={() =>
                                                            decide(a.value)
                                                        }
                                                    >
                                                        {a.label}
                                                    </button>
                                                ))}
                                            <button
                                                className={`${button} ml-auto flex items-center gap-2`}
                                                disabled={busy}
                                                onClick={next}
                                            >
                                                Skip <ChevronDown size={16} />
                                            </button>
                                        </div>
                                    )}
                                    <p className="text-xs text-muted-foreground">
                                        Skip leaves the decision unchanged.
                                        Press J outside a field to skip.
                                    </p>
                                </div>
                            )}
                            {actions.length === 0 && (
                                <button
                                    className={button}
                                    disabled={busy}
                                    onClick={next}
                                >
                                    Skip
                                </button>
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
                                                    {h.status
                                                        ? ` · ${h.status}`
                                                        : ""}
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
