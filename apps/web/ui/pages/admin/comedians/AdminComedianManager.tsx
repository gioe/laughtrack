"use client";

import type { AdminComedianListItem } from "@/lib/admin/comedianManagement";
import { Button } from "@/ui/components/ui/button";
import {
    AdminPagination,
    AdminSearchField,
    AdminSelectField,
    AdminToolbar,
    clampAdminPage,
} from "@/ui/pages/admin/shared/AdminControls";
import {
    Ban,
    ChevronDown,
    ChevronRight,
    ExternalLink,
    Save,
    ShieldCheck,
    X,
} from "lucide-react";
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

type WebsiteEdit = {
    website: string;
    websiteScrapingUrl: string;
};

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
    const [nameEdits, setNameEdits] = useState<Record<number, string>>({});
    const [websiteEdits, setWebsiteEdits] = useState<
        Record<number, WebsiteEdit>
    >({});
    const [openPodcastRows, setOpenPodcastRows] = useState<Set<number>>(
        new Set(),
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
                      row.website ?? "",
                      row.websiteScrapingUrl ?? "",
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
    const currentPage = clampAdminPage(page, totalPages);
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

    function nameValue(row: AdminComedianListItem) {
        return Object.hasOwn(nameEdits, row.id) ? nameEdits[row.id] : row.name;
    }

    function normalizedAdminName(name: string) {
        return name.trim().replace(/\s+/g, " ");
    }

    function normalizedUrl(value: string) {
        return value.trim() || null;
    }

    function isNameDirty(row: AdminComedianListItem) {
        return normalizedAdminName(nameValue(row)) !== row.name;
    }

    function websiteValue(row: AdminComedianListItem) {
        return websiteEdits[row.id]?.website ?? row.website ?? "";
    }

    function websiteScrapingUrlValue(row: AdminComedianListItem) {
        return (
            websiteEdits[row.id]?.websiteScrapingUrl ??
            row.websiteScrapingUrl ??
            ""
        );
    }

    function isWebsiteDirty(row: AdminComedianListItem) {
        return (
            normalizedUrl(websiteValue(row)) !== (row.website ?? null) ||
            normalizedUrl(websiteScrapingUrlValue(row)) !==
                (row.websiteScrapingUrl ?? null)
        );
    }

    function isRecordDirty(row: AdminComedianListItem) {
        return isNameDirty(row) || isWebsiteDirty(row);
    }

    function updateWebsiteEdit(
        row: AdminComedianListItem,
        patch: Partial<WebsiteEdit>,
    ) {
        setWebsiteEdits((current) => ({
            ...current,
            [row.id]: {
                website: websiteValue(row),
                websiteScrapingUrl: websiteScrapingUrlValue(row),
                ...patch,
            },
        }));
    }

    function togglePodcastRow(rowId: number) {
        setOpenPodcastRows((current) => {
            const next = new Set(current);
            if (next.has(rowId)) next.delete(rowId);
            else next.add(rowId);
            return next;
        });
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

    async function saveComedianRecord(row: AdminComedianListItem) {
        const name = normalizedAdminName(nameValue(row));
        if (!name || !isRecordDirty(row)) return;

        setStatus({ kind: "idle" });
        setPendingId(row.id);

        let res: Response;
        try {
            res = await fetch("/api/admin/comedians", {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    comedianId: row.id,
                    name,
                    website: normalizedUrl(websiteValue(row)),
                    websiteScrapingUrl: normalizedUrl(
                        websiteScrapingUrlValue(row),
                    ),
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
        setNameEdits((current) => {
            const next = { ...current };
            delete next[row.id];
            return next;
        });
        setWebsiteEdits((current) => {
            const next = { ...current };
            delete next[row.id];
            return next;
        });
        setStatus({ kind: "ok", message: `${row.name} record saved.` });
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

    async function unblockComedian(row: AdminComedianListItem) {
        setStatus({ kind: "idle" });
        setPendingId(row.id);

        let res: Response;
        try {
            res = await fetch("/api/admin/comedians", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action: "blocklist-remove",
                    comedianId: row.id,
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
        setStatus({
            kind: "ok",
            message: `${row.name} removed from blocklist.`,
        });
        startTransition(() => router.refresh());
    }

    return (
        <div className="space-y-4">
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
            </AdminToolbar>

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
            <div className="overflow-x-auto rounded-md border border-copper/25 bg-white">
                <div className="grid min-w-[1120px] grid-cols-[minmax(360px,1.15fr)_minmax(320px,0.95fr)_minmax(300px,0.8fr)] gap-6 border-b border-copper/20 bg-cedar px-4 py-3 font-dmSans text-caption font-semibold uppercase tracking-wide text-coconut-cream">
                    <div>Comedian</div>
                    <div>Parent relationship</div>
                    <div>Blocklist</div>
                </div>
                <ul className="divide-y divide-copper/15">
                    {pagedRows.map((row) => {
                        const parent = parentValue(row);
                        const candidates = parentCandidates(row);
                        const disabled = pendingId !== null || isPending;
                        const podcastsOpen = openPodcastRows.has(row.id);

                        return (
                            <li
                                key={row.id}
                                className="grid min-w-[1120px] items-start gap-x-6 gap-y-4 px-4 py-5 lg:grid-cols-[minmax(360px,1.15fr)_minmax(320px,0.95fr)_minmax(300px,0.8fr)]"
                            >
                                <div className="min-w-0 space-y-4">
                                    <div className="space-y-2">
                                        <h2 className="break-words font-gilroy-bold text-h3 text-cedar">
                                            {row.name}
                                        </h2>
                                        <div className="flex flex-wrap gap-2">
                                            {row.isBlocked && (
                                                <span className="rounded-full border border-red-700/30 bg-red-50 px-2 py-1 font-dmSans text-caption font-semibold text-red-900">
                                                    Blocked
                                                </span>
                                            )}
                                            {row.parent && (
                                                <span className="rounded-full border border-blue-800/40 bg-blue-50 px-2 py-1 font-dmSans text-caption font-semibold text-blue-950">
                                                    Child
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 font-dmSans text-body text-soft-charcoal">
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
                                        <span>
                                            {row.attributedPodcasts.length.toLocaleString()}{" "}
                                            podcasts
                                        </span>
                                    </div>
                                    {row.latestTicketPurchase ? (
                                        <div className="rounded-md border border-copper/20 bg-coconut-cream/35 p-3 font-dmSans">
                                            <a
                                                href={
                                                    row.latestTicketPurchase.url
                                                }
                                                target="_blank"
                                                rel="noreferrer"
                                                className="inline-flex items-center gap-2 text-body font-semibold text-copper-dark hover:underline"
                                            >
                                                Latest ticket purchase
                                                <ExternalLink className="h-4 w-4" />
                                            </a>
                                            <div className="mt-1 text-caption text-soft-charcoal">
                                                {row.latestTicketPurchase
                                                    .showName ??
                                                    "Untitled show"}{" "}
                                                ·{" "}
                                                {
                                                    row.latestTicketPurchase
                                                        .clubName
                                                }{" "}
                                                ·{" "}
                                                {formatDate(
                                                    row.latestTicketPurchase
                                                        .showDate,
                                                )}
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="rounded-md border border-soft-charcoal/20 bg-gray-50 px-3 py-2 font-dmSans text-caption text-soft-charcoal">
                                            No ticket purchase link found.
                                        </div>
                                    )}
                                    <div className="rounded-md border border-copper/20 bg-coconut-cream/35 p-3">
                                        <label className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                            Display name
                                        </label>
                                        <div className="mt-1 flex items-center gap-2">
                                            <input
                                                aria-label="Comedian name"
                                                type="text"
                                                value={nameValue(row)}
                                                onChange={(event) =>
                                                    setNameEdits((current) => ({
                                                        ...current,
                                                        [row.id]:
                                                            event.target.value,
                                                    }))
                                                }
                                                className="min-w-0 flex-1 rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                                            />
                                            <Button
                                                type="button"
                                                variant="outline"
                                                className="shrink-0 gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                disabled={
                                                    disabled ||
                                                    pendingId === row.id ||
                                                    !isRecordDirty(row) ||
                                                    !normalizedAdminName(
                                                        nameValue(row),
                                                    )
                                                }
                                                onClick={() =>
                                                    void saveComedianRecord(row)
                                                }
                                            >
                                                <Save className="h-4 w-4" />
                                                Save record
                                            </Button>
                                        </div>
                                        <div className="mt-3 grid gap-3">
                                            <label className="grid gap-1 font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                                Website
                                                <input
                                                    aria-label="Comedian website"
                                                    type="url"
                                                    value={websiteValue(row)}
                                                    onChange={(event) =>
                                                        updateWebsiteEdit(row, {
                                                            website:
                                                                event.target
                                                                    .value,
                                                        })
                                                    }
                                                    placeholder="https://example.com"
                                                    className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                                />
                                            </label>
                                            <label className="grid gap-1 font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                                Tour scrape URL
                                                <input
                                                    aria-label="Comedian website scraping URL"
                                                    type="url"
                                                    value={websiteScrapingUrlValue(
                                                        row,
                                                    )}
                                                    onChange={(event) =>
                                                        updateWebsiteEdit(row, {
                                                            websiteScrapingUrl:
                                                                event.target
                                                                    .value,
                                                        })
                                                    }
                                                    placeholder="https://example.com/tour"
                                                    className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                                />
                                            </label>
                                        </div>
                                    </div>
                                    <button
                                        type="button"
                                        aria-expanded={podcastsOpen}
                                        aria-controls={`comedian-podcasts-${row.id}`}
                                        onClick={() => togglePodcastRow(row.id)}
                                        className="inline-flex w-fit items-center gap-2 rounded-md border border-copper/30 bg-white px-3 py-2 font-dmSans text-body font-semibold text-cedar hover:bg-copper/10"
                                    >
                                        {podcastsOpen ? (
                                            <ChevronDown className="h-4 w-4" />
                                        ) : (
                                            <ChevronRight className="h-4 w-4" />
                                        )}
                                        Podcasts attributed
                                    </button>
                                </div>

                                <div className="space-y-4">
                                    <div className="space-y-2">
                                        <div className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                            Current parent
                                        </div>
                                        {parent ? (
                                            <div className="flex max-w-full items-center gap-2 rounded-md border border-green-700/40 bg-green-50 px-3 py-2 font-dmSans text-body font-semibold text-green-950">
                                                <span className="min-w-0 truncate">
                                                    {parent.name}
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
                                                    className="ml-auto shrink-0 rounded-sm p-1 text-green-950 hover:bg-green-100"
                                                    aria-label={`Clear parent for ${row.name}`}
                                                >
                                                    <X className="h-4 w-4" />
                                                </button>
                                            </div>
                                        ) : (
                                            <div className="rounded-md border border-soft-charcoal/20 bg-gray-50 px-3 py-2 font-dmSans text-body text-soft-charcoal">
                                                No parent assigned
                                            </div>
                                        )}
                                    </div>

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
                                        className="gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
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

                                <div className="space-y-4">
                                    <div className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                        Blocklist state
                                    </div>
                                    {row.isBlocked ? (
                                        <div className="space-y-3">
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
                                            <Button
                                                type="button"
                                                variant="outline"
                                                className="gap-2 border-green-800/40 bg-white text-green-950 hover:bg-green-50 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                disabled={
                                                    disabled ||
                                                    pendingId === row.id
                                                }
                                                onClick={() =>
                                                    void unblockComedian(row)
                                                }
                                            >
                                                <ShieldCheck className="h-4 w-4" />
                                                Remove from blocklist
                                            </Button>
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
                                                className="gap-2 border-red-800/40 bg-white text-red-950 hover:bg-red-50 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
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

                                <div
                                    id={`comedian-podcasts-${row.id}`}
                                    hidden={!podcastsOpen}
                                    className={`lg:col-span-3 ${
                                        podcastsOpen ? "" : "hidden"
                                    }`}
                                >
                                    <div className="rounded-md border border-copper/20 bg-coconut-cream/25 p-4">
                                        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                                            <h3 className="font-gilroy-bold text-h3 text-cedar">
                                                Podcasts attributed
                                            </h3>
                                            <span className="font-dmSans text-caption font-semibold text-soft-charcoal">
                                                {row.attributedPodcasts.length.toLocaleString()}{" "}
                                                total
                                            </span>
                                        </div>
                                        {row.attributedPodcasts.length === 0 ? (
                                            <p className="font-dmSans text-body text-soft-charcoal">
                                                No podcasts are attributed to
                                                this comedian.
                                            </p>
                                        ) : (
                                            <div className="overflow-x-auto rounded-md border border-copper/15 bg-white">
                                                <table className="min-w-full divide-y divide-copper/15 text-left font-dmSans text-body">
                                                    <thead className="bg-cedar text-caption uppercase tracking-wide text-coconut-cream">
                                                        <tr>
                                                            <th className="px-3 py-2">
                                                                Podcast
                                                            </th>
                                                            <th className="px-3 py-2">
                                                                Attribution
                                                            </th>
                                                            <th className="px-3 py-2">
                                                                Review
                                                            </th>
                                                            <th className="px-3 py-2">
                                                                Links
                                                            </th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-copper/10">
                                                        {row.attributedPodcasts.map(
                                                            (podcast) => (
                                                                <tr
                                                                    key={`${podcast.id}-${podcast.associationType}-${podcast.source}`}
                                                                >
                                                                    <td className="px-3 py-3 align-top">
                                                                        <div className="font-semibold text-cedar">
                                                                            {
                                                                                podcast.title
                                                                            }
                                                                        </div>
                                                                        <div className="text-caption text-soft-charcoal">
                                                                            ID{" "}
                                                                            {
                                                                                podcast.id
                                                                            }
                                                                        </div>
                                                                    </td>
                                                                    <td className="px-3 py-3 align-top text-soft-charcoal">
                                                                        <div className="font-semibold text-cedar">
                                                                            {
                                                                                podcast.associationType
                                                                            }
                                                                        </div>
                                                                        <div className="text-caption">
                                                                            {
                                                                                podcast.source
                                                                            }{" "}
                                                                            ·{" "}
                                                                            {Math.round(
                                                                                podcast.confidence *
                                                                                    100,
                                                                            )}
                                                                            %
                                                                        </div>
                                                                    </td>
                                                                    <td className="px-3 py-3 align-top">
                                                                        <span className="rounded-full border border-green-700/30 bg-green-50 px-2 py-1 text-caption font-semibold text-green-900">
                                                                            {
                                                                                podcast.reviewStatus
                                                                            }
                                                                        </span>
                                                                    </td>
                                                                    <td className="px-3 py-3 align-top">
                                                                        <div className="flex flex-wrap gap-3 text-caption font-semibold">
                                                                            <a
                                                                                href={`/podcast/${podcast.slug}`}
                                                                                target="_blank"
                                                                                className="inline-flex items-center gap-1 text-copper-dark hover:underline"
                                                                            >
                                                                                Public
                                                                                page
                                                                                <ExternalLink className="h-3.5 w-3.5" />
                                                                            </a>
                                                                            {podcast.feedUrl && (
                                                                                <a
                                                                                    href={
                                                                                        podcast.feedUrl
                                                                                    }
                                                                                    target="_blank"
                                                                                    rel="noreferrer"
                                                                                    className="inline-flex items-center gap-1 text-copper-dark hover:underline"
                                                                                >
                                                                                    RSS
                                                                                    <ExternalLink className="h-3.5 w-3.5" />
                                                                                </a>
                                                                            )}
                                                                            {podcast.websiteUrl && (
                                                                                <a
                                                                                    href={
                                                                                        podcast.websiteUrl
                                                                                    }
                                                                                    target="_blank"
                                                                                    rel="noreferrer"
                                                                                    className="inline-flex items-center gap-1 text-copper-dark hover:underline"
                                                                                >
                                                                                    Website
                                                                                    <ExternalLink className="h-3.5 w-3.5" />
                                                                                </a>
                                                                            )}
                                                                        </div>
                                                                    </td>
                                                                </tr>
                                                            ),
                                                        )}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </li>
                        );
                    })}
                </ul>
            </div>
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
        </div>
    );
}
