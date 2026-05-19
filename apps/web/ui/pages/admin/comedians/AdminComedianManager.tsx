"use client";

import type { AdminComedianListItem } from "@/lib/admin/comedianManagement";
import { Button } from "@/ui/components/ui/button";
import { Ban, Save, Search, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, useTransition } from "react";

type Props = {
    comedians: AdminComedianListItem[];
};

type SortMode = "name-asc" | "name-desc" | "popularity-desc" | "popularity-asc";

type Status = {
    kind: "idle" | "ok" | "error";
    message?: string;
};

const PAGE_SIZE_OPTIONS = [25, 50, 100, 200];

function formatDate(iso: string | null) {
    if (!iso) return null;
    return iso.replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

function compareByName(a: AdminComedianListItem, b: AdminComedianListItem) {
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
}

function sortRows(rows: AdminComedianListItem[], sort: SortMode) {
    return [...rows].sort((a, b) => {
        if (sort === "name-desc") return compareByName(b, a);
        if (sort === "popularity-desc") {
            return b.popularity - a.popularity || compareByName(a, b);
        }
        if (sort === "popularity-asc") {
            return a.popularity - b.popularity || compareByName(a, b);
        }
        return compareByName(a, b);
    });
}

function clampPage(page: number, totalPages: number) {
    return Math.min(Math.max(page, 1), Math.max(totalPages, 1));
}

function PaginationControls({
    page,
    pageSize,
    totalItems,
    onPageChange,
    onPageSizeChange,
}: {
    page: number;
    pageSize: number;
    totalItems: number;
    onPageChange: (page: number) => void;
    onPageSizeChange: (pageSize: number) => void;
}) {
    const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
    const start = totalItems === 0 ? 0 : (page - 1) * pageSize + 1;
    const end = Math.min(page * pageSize, totalItems);

    return (
        <div className="flex flex-col gap-3 rounded-md border border-copper/25 bg-white px-3 py-2 font-dmSans text-body text-cedar md:flex-row md:items-center md:justify-between">
            <div className="font-semibold">
                {start}-{end} of {totalItems} comedians
            </div>
            <div className="flex flex-wrap items-center gap-2">
                <label className="flex items-center gap-2 font-semibold">
                    Per page
                    <select
                        value={pageSize}
                        onChange={(event) =>
                            onPageSizeChange(Number(event.target.value))
                        }
                        className="rounded-md border border-soft-charcoal/30 bg-white px-2 py-1 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                    >
                        {PAGE_SIZE_OPTIONS.map((option) => (
                            <option key={option} value={option}>
                                {option}
                            </option>
                        ))}
                    </select>
                </label>
                <Button
                    type="button"
                    variant="outline"
                    className="border-copper-dark bg-white text-copper-dark disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                    disabled={page <= 1}
                    onClick={() => onPageChange(page - 1)}
                >
                    Previous
                </Button>
                <span className="font-semibold">
                    Page {page} of {totalPages}
                </span>
                <Button
                    type="button"
                    variant="outline"
                    className="border-copper-dark bg-white text-copper-dark disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                    disabled={page >= totalPages}
                    onClick={() => onPageChange(page + 1)}
                >
                    Next
                </Button>
            </div>
        </div>
    );
}

export default function AdminComedianManager({ comedians }: Props) {
    const router = useRouter();
    const [rows, setRows] = useState(comedians);
    const [query, setQuery] = useState("");
    const [sort, setSort] = useState<SortMode>("name-asc");
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(50);
    const [parentSearches, setParentSearches] = useState<
        Record<number, string>
    >({});
    const [selectedParents, setSelectedParents] = useState<
        Record<number, AdminComedianListItem["parent"]>
    >({});
    const [blockReasons, setBlockReasons] = useState<Record<number, string>>(
        {},
    );
    const [pendingId, setPendingId] = useState<number | null>(null);
    const [status, setStatus] = useState<Status>({ kind: "idle" });
    const [isPending, startTransition] = useTransition();

    const visibleRows = useMemo(() => {
        const normalizedQuery = query.trim().toLowerCase();
        const filtered = normalizedQuery
            ? rows.filter((row) => {
                  return [
                      row.name,
                      row.parent?.name ?? "",
                      row.blockReason ?? "",
                      row.blockAddedBy ?? "",
                  ]
                      .join(" ")
                      .toLowerCase()
                      .includes(normalizedQuery);
              })
            : rows;
        return sortRows(filtered, sort);
    }, [query, rows, sort]);
    const totalPages = Math.max(1, Math.ceil(visibleRows.length / pageSize));
    const currentPage = clampPage(page, totalPages);
    const pageStart = (currentPage - 1) * pageSize;
    const pagedRows = visibleRows.slice(pageStart, pageStart + pageSize);

    useEffect(() => {
        setPage(1);
    }, [query, sort, pageSize]);

    function parentValue(row: AdminComedianListItem) {
        return Object.hasOwn(selectedParents, row.id)
            ? selectedParents[row.id]
            : row.parent;
    }

    function isParentDirty(row: AdminComedianListItem) {
        if (!Object.hasOwn(selectedParents, row.id)) return false;
        return selectedParents[row.id]?.id !== row.parent?.id;
    }

    function parentCandidates(row: AdminComedianListItem) {
        const search = parentSearches[row.id]?.trim().toLowerCase() ?? "";
        if (!search) return [];
        return rows
            .filter((candidate) => {
                return (
                    candidate.id !== row.id &&
                    candidate.name.toLowerCase().includes(search)
                );
            })
            .sort(compareByName)
            .slice(0, 8);
    }

    async function saveParent(row: AdminComedianListItem) {
        const parent = parentValue(row);
        setStatus({ kind: "idle" });
        setPendingId(row.id);

        let res: Response;
        try {
            res = await fetch("/api/admin/comedians", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action: "set-parent",
                    comedianId: row.id,
                    parentComedianId: parent?.id ?? null,
                }),
            });
        } catch (error) {
            setPendingId(null);
            setStatus({
                kind: "error",
                message:
                    error instanceof Error ? error.message : "Network error",
            });
            return;
        }

        setPendingId(null);
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            setStatus({
                kind: "error",
                message: body.error ?? `Request failed (${res.status})`,
            });
            return;
        }

        const body = (await res.json()) as { comedian: AdminComedianListItem };
        setRows((current) =>
            current.map((currentRow) =>
                currentRow.id === row.id ? body.comedian : currentRow,
            ),
        );
        setSelectedParents((current) => {
            const next = { ...current };
            delete next[row.id];
            return next;
        });
        setParentSearches((current) => ({ ...current, [row.id]: "" }));
        setStatus({ kind: "ok", message: `${row.name} relationship saved.` });
        startTransition(() => router.refresh());
    }

    async function blockComedian(row: AdminComedianListItem) {
        const reason = blockReasons[row.id]?.trim() ?? "";
        if (!reason) return;

        setStatus({ kind: "idle" });
        setPendingId(row.id);

        let res: Response;
        try {
            res = await fetch("/api/admin/comedians", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action: "blocklist-add",
                    comedianId: row.id,
                    reason,
                }),
            });
        } catch (error) {
            setPendingId(null);
            setStatus({
                kind: "error",
                message:
                    error instanceof Error ? error.message : "Network error",
            });
            return;
        }

        setPendingId(null);
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            setStatus({
                kind: "error",
                message: body.error ?? `Request failed (${res.status})`,
            });
            return;
        }

        const body = (await res.json()) as { comedian: AdminComedianListItem };
        setRows((current) =>
            current.map((currentRow) =>
                currentRow.id === row.id ? body.comedian : currentRow,
            ),
        );
        setBlockReasons((current) => ({ ...current, [row.id]: "" }));
        setStatus({ kind: "ok", message: `${row.name} added to blocklist.` });
        startTransition(() => router.refresh());
    }

    return (
        <div className="space-y-4">
            <div className="grid gap-3 rounded-md border border-copper/25 bg-white p-4 md:grid-cols-[minmax(0,1fr)_220px]">
                <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                    Search comedians
                    <span className="relative">
                        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-soft-charcoal" />
                        <input
                            type="search"
                            value={query}
                            onChange={(event) => setQuery(event.target.value)}
                            className="w-full rounded-md border border-soft-charcoal/30 bg-white py-2 pl-10 pr-3 font-dmSans text-body text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                            placeholder="Name, parent, block reason"
                        />
                    </span>
                </label>
                <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                    Sort
                    <select
                        value={sort}
                        onChange={(event) =>
                            setSort(event.target.value as SortMode)
                        }
                        className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                    >
                        <option value="name-asc">Name A-Z</option>
                        <option value="name-desc">Name Z-A</option>
                        <option value="popularity-desc">
                            Popularity high-low
                        </option>
                        <option value="popularity-asc">
                            Popularity low-high
                        </option>
                    </select>
                </label>
            </div>

            {status.kind === "ok" && (
                <p className="rounded-md border border-green-700/30 bg-green-50 px-3 py-2 font-dmSans text-body text-green-900">
                    {status.message}
                </p>
            )}
            {status.kind === "error" && (
                <p className="rounded-md border border-red-700/30 bg-red-50 px-3 py-2 font-dmSans text-body text-red-900">
                    {status.message}
                </p>
            )}

            <PaginationControls
                page={currentPage}
                pageSize={pageSize}
                totalItems={visibleRows.length}
                onPageChange={(nextPage) =>
                    setPage(clampPage(nextPage, totalPages))
                }
                onPageSizeChange={setPageSize}
            />
            <div className="overflow-x-auto rounded-md border border-copper/25 bg-white">
                <div className="grid min-w-[980px] grid-cols-[minmax(260px,1fr)_minmax(260px,420px)_minmax(260px,380px)] gap-4 border-b border-copper/20 bg-cedar px-4 py-3 font-dmSans text-caption font-semibold uppercase tracking-wide text-coconut-cream">
                    <div>Comedian</div>
                    <div>Parent relationship</div>
                    <div>Blocklist</div>
                </div>
                <ul className="divide-y divide-copper/15">
                    {pagedRows.map((row) => {
                        const parent = parentValue(row);
                        const candidates = parentCandidates(row);
                        const disabled = pendingId !== null || isPending;

                        return (
                            <li
                                key={row.id}
                                className="grid min-w-[980px] gap-4 px-4 py-4 lg:grid-cols-[minmax(260px,1fr)_minmax(260px,420px)_minmax(260px,380px)]"
                            >
                                <div className="min-w-0">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <h2 className="font-gilroy-bold text-h3 text-cedar">
                                            {row.name}
                                        </h2>
                                        {row.isBlocked && (
                                            <span className="rounded-full border border-red-700/30 bg-red-50 px-2 py-1 font-dmSans text-caption font-semibold text-red-900">
                                                Blocked
                                            </span>
                                        )}
                                        {row.parent && (
                                            <span className="rounded-full border border-copper/30 bg-coconut-cream px-2 py-1 font-dmSans text-caption font-semibold text-cedar">
                                                Child
                                            </span>
                                        )}
                                    </div>
                                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-dmSans text-body text-soft-charcoal">
                                        <span>ID {row.id}</span>
                                        <span>
                                            Popularity{" "}
                                            {row.popularity.toLocaleString()}
                                        </span>
                                        <span>
                                            {row.totalShows.toLocaleString()}{" "}
                                            shows
                                        </span>
                                        <span>
                                            {row.childCount.toLocaleString()}{" "}
                                            children
                                        </span>
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    {parent ? (
                                        <div className="flex w-fit max-w-full items-center gap-2 rounded-md border border-green-700/40 bg-green-50 px-3 py-2 font-dmSans text-body font-semibold text-green-950">
                                            <span className="min-w-0 truncate">
                                                Parent: {parent.name}
                                            </span>
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    setSelectedParents(
                                                        (current) => ({
                                                            ...current,
                                                            [row.id]: null,
                                                        }),
                                                    )
                                                }
                                                className="rounded-sm p-1 text-green-950 hover:bg-green-100"
                                                aria-label={`Clear parent for ${row.name}`}
                                            >
                                                <X className="h-4 w-4" />
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="font-dmSans text-body text-soft-charcoal">
                                            No parent assigned
                                        </div>
                                    )}

                                    <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                        Find parent
                                        <input
                                            type="search"
                                            value={parentSearches[row.id] ?? ""}
                                            onChange={(event) =>
                                                setParentSearches(
                                                    (current) => ({
                                                        ...current,
                                                        [row.id]:
                                                            event.target.value,
                                                    }),
                                                )
                                            }
                                            className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                            placeholder="Search parent name"
                                        />
                                    </label>
                                    {candidates.length > 0 && (
                                        <div className="flex flex-wrap gap-2">
                                            {candidates.map((candidate) => (
                                                <button
                                                    key={candidate.id}
                                                    type="button"
                                                    onClick={() =>
                                                        setSelectedParents(
                                                            (current) => ({
                                                                ...current,
                                                                [row.id]: {
                                                                    id: candidate.id,
                                                                    name: candidate.name,
                                                                },
                                                            }),
                                                        )
                                                    }
                                                    className="rounded-md border border-copper/40 bg-coconut-cream px-3 py-2 font-dmSans text-body font-semibold text-cedar hover:bg-copper/10"
                                                >
                                                    {candidate.name}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="gap-2 border-copper/40 text-cedar disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                        disabled={
                                            disabled ||
                                            !isParentDirty(row) ||
                                            pendingId === row.id
                                        }
                                        onClick={() => void saveParent(row)}
                                    >
                                        <Save className="h-4 w-4" />
                                        Save relationship
                                    </Button>
                                </div>

                                <div className="space-y-3">
                                    {row.isBlocked ? (
                                        <div className="rounded-md border border-red-700/25 bg-red-50 p-3 font-dmSans text-body text-red-950">
                                            <div className="font-semibold">
                                                {row.blockReason}
                                            </div>
                                            <div className="mt-1 text-caption text-red-900">
                                                {row.blockAddedBy}
                                                {row.blockAddedAt
                                                    ? ` · ${formatDate(row.blockAddedAt)}`
                                                    : ""}
                                            </div>
                                        </div>
                                    ) : (
                                        <>
                                            <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                                Blocklist reason
                                                <input
                                                    type="text"
                                                    value={
                                                        blockReasons[row.id] ??
                                                        ""
                                                    }
                                                    onChange={(event) =>
                                                        setBlockReasons(
                                                            (current) => ({
                                                                ...current,
                                                                [row.id]:
                                                                    event.target
                                                                        .value,
                                                            }),
                                                        )
                                                    }
                                                    className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                                    maxLength={1000}
                                                />
                                            </label>
                                            <Button
                                                type="button"
                                                variant="outline"
                                                className="gap-2 border-red-800/40 text-red-950 hover:bg-red-50 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                disabled={
                                                    disabled ||
                                                    pendingId === row.id ||
                                                    !blockReasons[
                                                        row.id
                                                    ]?.trim()
                                                }
                                                onClick={() =>
                                                    void blockComedian(row)
                                                }
                                            >
                                                <Ban className="h-4 w-4" />
                                                Add to blocklist
                                            </Button>
                                        </>
                                    )}
                                </div>
                            </li>
                        );
                    })}
                </ul>
            </div>
            <PaginationControls
                page={currentPage}
                pageSize={pageSize}
                totalItems={visibleRows.length}
                onPageChange={(nextPage) =>
                    setPage(clampPage(nextPage, totalPages))
                }
                onPageSizeChange={setPageSize}
            />
        </div>
    );
}
