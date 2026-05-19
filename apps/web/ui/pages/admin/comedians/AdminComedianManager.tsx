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
import { Ban, Save, ShieldCheck, X } from "lucide-react";
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

    function isNameDirty(row: AdminComedianListItem) {
        return normalizedAdminName(nameValue(row)) !== row.name;
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
        if (!name || name === row.name) return;

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
                                            <span className="rounded-full border border-blue-800/40 bg-blue-50 px-2 py-1 font-dmSans text-caption font-semibold text-blue-950">
                                                Child
                                            </span>
                                        )}
                                    </div>
                                    <div className="mt-3 grid max-w-xl gap-2">
                                        <label className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                            Comedian name
                                            <input
                                                type="text"
                                                value={nameValue(row)}
                                                onChange={(event) =>
                                                    setNameEdits((current) => ({
                                                        ...current,
                                                        [row.id]:
                                                            event.target.value,
                                                    }))
                                                }
                                                className="mt-1 block w-full rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                                            />
                                        </label>
                                        <Button
                                            type="button"
                                            variant="outline"
                                            className="w-fit gap-2 border-copper/40 text-cedar disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                            disabled={
                                                disabled ||
                                                pendingId === row.id ||
                                                !isNameDirty(row) ||
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
                                                className="gap-2 border-green-800/40 text-green-950 hover:bg-green-50 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
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
