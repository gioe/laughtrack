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

type RecordTypeFilter = "all" | "canonical" | "alias" | "blocked";
type PresenceFilter = "all" | "has" | "missing";
type PodcastFilter = "all" | "accepted" | "pending" | "none";
type ShowFilter = "all" | "has" | "none";

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
    const [recordType, setRecordType] = useState<RecordTypeFilter>("all");
    const [imageFilter, setImageFilter] = useState<PresenceFilter>("all");
    const [podcastFilter, setPodcastFilter] = useState<PodcastFilter>("all");
    const [showFilter, setShowFilter] = useState<ShowFilter>("all");
    const [instagramFilter, setInstagramFilter] =
        useState<PresenceFilter>("all");
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
                if (recordType === "blocked" && !row.isBlocked) {
                    return false;
                }
                if (
                    recordType === "canonical" &&
                    (row.isBlocked || row.parent !== null)
                ) {
                    return false;
                }
                if (
                    recordType === "alias" &&
                    (row.isBlocked || row.parent === null)
                ) {
                    return false;
                }
                if (imageFilter === "has" && !row.hasImage) {
                    return false;
                }
                if (imageFilter === "missing" && row.hasImage) {
                    return false;
                }
                if (
                    podcastFilter === "accepted" &&
                    row.attributedPodcasts.length === 0
                ) {
                    return false;
                }
                if (
                    podcastFilter === "pending" &&
                    row.podcastCandidateReviews.length === 0
                ) {
                    return false;
                }
                if (
                    podcastFilter === "none" &&
                    (row.attributedPodcasts.length > 0 ||
                        row.podcastCandidateReviews.length > 0)
                ) {
                    return false;
                }
                if (showFilter === "has" && row.totalShows === 0) {
                    return false;
                }
                if (showFilter === "none" && row.totalShows > 0) {
                    return false;
                }
                const hasInstagram = Boolean(row.instagramAccount?.trim());
                if (instagramFilter === "has" && !hasInstagram) {
                    return false;
                }
                if (instagramFilter === "missing" && hasInstagram) {
                    return false;
                }
                if (!normalizedQuery) return true;
                return [
                    row.name,
                    row.website ?? "",
                    row.websiteScrapingUrl ?? "",
                    row.blockReason ?? "",
                    row.blockAddedBy ?? "",
                    ...(recordType === "canonical"
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
    }, [
        childrenByParentId,
        imageFilter,
        instagramFilter,
        podcastFilter,
        query,
        recordType,
        rows,
        showFilter,
        sort,
    ]);

    const totalPages = Math.max(1, Math.ceil(visibleRows.length / pageSize));
    const currentPage = clampAdminPage(page, totalPages);
    const pageStart = (currentPage - 1) * pageSize;
    const pagedRows = visibleRows.slice(pageStart, pageStart + pageSize);

    useEffect(() => {
        setPage(1);
    }, [
        imageFilter,
        instagramFilter,
        pageSize,
        podcastFilter,
        query,
        recordType,
        showFilter,
        sort,
    ]);

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
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    <AdminSelectField
                        label="Record type"
                        value={recordType}
                        onChange={setRecordType}
                        options={[
                            { value: "all", label: "All records" },
                            { value: "canonical", label: "Canonical" },
                            { value: "alias", label: "Aliases" },
                            { value: "blocked", label: "Blocked" },
                        ]}
                    />
                    <AdminSelectField
                        label="Image"
                        value={imageFilter}
                        onChange={setImageFilter}
                        options={[
                            { value: "all", label: "All images" },
                            { value: "has", label: "Has image" },
                            { value: "missing", label: "No image" },
                        ]}
                    />
                    <AdminSelectField
                        label="Podcast"
                        value={podcastFilter}
                        onChange={setPodcastFilter}
                        options={[
                            { value: "all", label: "All podcasts" },
                            { value: "accepted", label: "Accepted podcast" },
                            { value: "pending", label: "Pending review" },
                            { value: "none", label: "No podcast" },
                        ]}
                    />
                    <AdminSelectField
                        label="Shows"
                        value={showFilter}
                        onChange={setShowFilter}
                        options={[
                            { value: "all", label: "All show counts" },
                            { value: "has", label: "Has shows" },
                            { value: "none", label: "No shows" },
                        ]}
                    />
                    <AdminSelectField
                        label="Instagram"
                        value={instagramFilter}
                        onChange={setInstagramFilter}
                        options={[
                            { value: "all", label: "All Instagram" },
                            { value: "has", label: "Has Instagram" },
                            { value: "missing", label: "No Instagram" },
                        ]}
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
                                recordType === "canonical"
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
