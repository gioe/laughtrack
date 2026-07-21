"use client";

import type { AdminComedianListItem } from "@/lib/admin/comedianManagement";
import {
    AdminPagination,
    AdminSearchField,
    AdminSelectField,
    AdminToolbar,
    clampAdminPage,
} from "@/ui/pages/admin/shared/AdminControls";
import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AdminComedianRow } from "./AdminComedianRow";

type Props = {
    comedians: AdminComedianListItem[];
};

type Status = {
    kind: "idle" | "ok" | "error";
    message?: string;
};

type SortMode =
    | "name-asc"
    | "name-desc"
    | "created-desc"
    | "created-asc"
    | "popularity-desc"
    | "popularity-asc";

function compareByName(a: AdminComedianListItem, b: AdminComedianListItem) {
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
}

function acceptedPodcastSearchValues(row: AdminComedianListItem) {
    return row.attributedPodcasts
        .filter((podcast) => podcast.reviewStatus === "accepted")
        .flatMap((podcast) => [podcast.title, podcast.feedUrl ?? ""]);
}

function sortRows(rows: AdminComedianListItem[], sort: SortMode) {
    return [...rows].sort((a, b) => {
        if (sort === "name-desc") return compareByName(b, a);
        if (sort === "created-desc") {
            return (
                new Date(b.createdAt).getTime() -
                    new Date(a.createdAt).getTime() ||
                b.id - a.id ||
                compareByName(a, b)
            );
        }
        if (sort === "created-asc") {
            return (
                new Date(a.createdAt).getTime() -
                    new Date(b.createdAt).getTime() ||
                a.id - b.id ||
                compareByName(a, b)
            );
        }
        if (sort === "popularity-desc") {
            return b.popularity - a.popularity || compareByName(a, b);
        }
        if (sort === "popularity-asc") {
            return a.popularity - b.popularity || compareByName(a, b);
        }
        return compareByName(a, b);
    });
}

export default function AdminComedianManager({ comedians }: Props) {
    const [rows, setRows] = useState(comedians);
    const [query, setQuery] = useState("");
    const [sort, setSort] = useState<SortMode>("name-asc");
    const [blockedOnly, setBlockedOnly] = useState(false);
    const [canonicalOnly, setCanonicalOnly] = useState(false);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(50);
    const [pendingRowIds, setPendingRowIds] = useState<Set<number>>(
        () => new Set(),
    );
    const [status, setStatus] = useState<Status>({ kind: "idle" });

    const childrenByParentId = useMemo(() => {
        const map = new Map<number, AdminComedianListItem[]>();
        rows.forEach((row) => {
            if (!row.parent) return;
            const children = map.get(row.parent.id) ?? [];
            children.push(row);
            map.set(row.parent.id, children);
        });
        for (const children of map.values()) children.sort(compareByName);
        return map;
    }, [rows]);

    const visibleRows = useMemo(() => {
        const normalizedQuery = query.trim().toLowerCase();
        return sortRows(
            rows.filter((row) => {
                if (blockedOnly && !row.isBlocked) {
                    return false;
                }
                if (canonicalOnly && (row.isBlocked || row.parent !== null)) {
                    return false;
                }
                if (!normalizedQuery) return true;
                return [
                    row.name,
                    row.website ?? "",
                    row.websiteScrapingUrl ?? "",
                    row.blockReason ?? "",
                    row.blockAddedBy ?? "",
                    ...(canonicalOnly
                        ? []
                        : (childrenByParentId.get(row.id) ?? []).map(
                              (child) => child.name,
                          )),
                    ...acceptedPodcastSearchValues(row),
                ]
                    .join(" ")
                    .toLowerCase()
                    .includes(normalizedQuery);
            }),
            sort,
        );
    }, [blockedOnly, canonicalOnly, childrenByParentId, query, rows, sort]);

    const totalPages = Math.max(1, Math.ceil(visibleRows.length / pageSize));
    const currentPage = clampAdminPage(page, totalPages);
    const pageStart = (currentPage - 1) * pageSize;
    const pagedRows = visibleRows.slice(pageStart, pageStart + pageSize);

    useEffect(() => {
        setPage(1);
    }, [blockedOnly, canonicalOnly, pageSize, query, sort]);

    useEffect(() => {
        setRows(comedians);
    }, [comedians]);

    function updateCanonicalRow(updatedRow: AdminComedianListItem) {
        setRows((current) =>
            current.map((row) => (row.id === updatedRow.id ? updatedRow : row)),
        );
    }

    const updatePendingRow = useCallback((rowId: number, pending: boolean) => {
        setPendingRowIds((current) => {
            if (current.has(rowId) === pending) return current;
            const next = new Set(current);
            if (pending) next.add(rowId);
            else next.delete(rowId);
            return next;
        });
    }, []);

    const pagination = (
        <AdminPagination
            page={currentPage}
            pageSize={pageSize}
            totalItems={visibleRows.length}
            label="comedians"
            onPageChange={(nextPage) =>
                setPage(clampAdminPage(nextPage, totalPages))
            }
            onPageSizeChange={setPageSize}
        />
    );

    return (
        <div className="space-y-4">
            {pendingRowIds.size > 0 && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-canvas/80 backdrop-blur-[1px]">
                    <div
                        role="status"
                        aria-live="polite"
                        className="flex items-center gap-3 rounded-md border border-copper/25 bg-surface-elevated px-5 py-4 font-dmSans text-body font-semibold text-foreground shadow-floating"
                    >
                        <Loader2 className="h-5 w-5 animate-spin text-copper" />
                        Updating comedian
                    </div>
                </div>
            )}
            {status.kind !== "idle" && (
                <div
                    role="status"
                    aria-live="polite"
                    className="fixed inset-x-0 top-4 z-[60] px-4"
                >
                    <p
                        className={
                            status.kind === "ok"
                                ? "mx-auto max-w-4xl rounded-md border border-green-700/30 bg-green-50 px-4 py-3 text-center font-dmSans text-body font-semibold text-green-900 shadow-floating"
                                : "mx-auto max-w-4xl rounded-md border border-red-700/30 bg-red-50 px-4 py-3 text-center font-dmSans text-body font-semibold text-red-900 shadow-floating"
                        }
                    >
                        {status.message}
                    </p>
                </div>
            )}
            <AdminToolbar>
                <AdminSearchField
                    label="Search comedians"
                    value={query}
                    onChange={setQuery}
                    placeholder="Name, parent, block reason"
                />
                <AdminSelectField
                    label="Sort"
                    value={sort}
                    onChange={setSort}
                    options={[
                        { value: "name-asc", label: "Name A-Z" },
                        { value: "name-desc", label: "Name Z-A" },
                        { value: "created-desc", label: "Newest added" },
                        { value: "created-asc", label: "Oldest added" },
                        {
                            value: "popularity-desc",
                            label: "Popularity high-low",
                        },
                        {
                            value: "popularity-asc",
                            label: "Popularity low-high",
                        },
                    ]}
                />
                <div className="flex flex-wrap items-center gap-3 self-end">
                    <label className="inline-flex h-10 items-center gap-2 rounded-md border border-strong bg-surface-elevated px-3 font-dmSans text-body font-semibold text-foreground">
                        <input
                            type="checkbox"
                            checked={blockedOnly}
                            onChange={(event) => {
                                const checked = event.target.checked;
                                setBlockedOnly(checked);
                                if (checked) setCanonicalOnly(false);
                            }}
                            className="h-4 w-4 accent-copper-dark"
                        />
                        Blocked
                    </label>
                    <label className="inline-flex h-10 items-center gap-2 rounded-md border border-strong bg-surface-elevated px-3 font-dmSans text-body font-semibold text-foreground">
                        <input
                            type="checkbox"
                            checked={canonicalOnly}
                            onChange={(event) => {
                                const checked = event.target.checked;
                                setCanonicalOnly(checked);
                                if (checked) setBlockedOnly(false);
                            }}
                            className="h-4 w-4 accent-copper-dark"
                        />
                        Canonical
                    </label>
                </div>
            </AdminToolbar>
            {pagination}
            <div className="rounded-md border border-copper/20 bg-surface-elevated">
                <div className="border-b border-copper/20 bg-cedar px-4 py-3 font-dmSans text-caption font-semibold uppercase tracking-wide text-foreground">
                    Comedians
                </div>
                <ul className="divide-y divide-copper/15">
                    {pagedRows.map((row) => (
                        <AdminComedianRow
                            key={row.id}
                            row={row}
                            allRows={rows}
                            children={
                                canonicalOnly
                                    ? []
                                    : (childrenByParentId.get(row.id) ?? [])
                            }
                            onRowChange={updateCanonicalRow}
                            globallyDisabled={pendingRowIds.size > 0}
                            onPendingChange={updatePendingRow}
                            onStatusChange={setStatus}
                        />
                    ))}
                </ul>
            </div>
            {pagination}
        </div>
    );
}
