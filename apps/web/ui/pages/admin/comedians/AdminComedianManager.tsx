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
    Trash2,
    Upload,
    X,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, useTransition } from "react";

type Props = {
    comedians: AdminComedianListItem[];
};

type SortMode =
    | "name-asc"
    | "name-desc"
    | "created-desc"
    | "created-asc"
    | "popularity-desc"
    | "popularity-asc";

type Status = {
    kind: "idle" | "ok" | "error";
    message?: string;
};

type WebsiteEdit = {
    website: string;
    websiteScrapingUrl: string;
};

type ImageCandidate = {
    imageUrl: string;
    heroImageUrl?: string | null;
    sourcePage: string | null;
    width: number | null;
    height: number | null;
    mimeType: string | null;
    score: number;
    reasons: string[];
};

type ImagePreview = {
    avatarDataUrl: string;
    heroDataUrl: string;
    warnings: string[];
};

type ImageDiscoveryState = {
    kind: "idle" | "loading" | "ready" | "error";
    candidates: ImageCandidate[];
    selectedCandidate: ImageCandidate | null;
    preview: ImagePreview | null;
    error?: string;
};

type ManualImageUrls = {
    headshot: string;
    hero: string;
};

function formatDate(iso: string | null) {
    if (!iso) return null;
    return iso.replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

function formatDimensions(width: number | null, height: number | null) {
    return width && height ? `${width}x${height}` : "Unknown size";
}

function legacyComedianImageUrl(row: AdminComedianListItem) {
    return row.legacyImageUrl;
}

function currentAvatarUrl(row: AdminComedianListItem) {
    return row.activeImageAsset?.avatarUrl ?? legacyComedianImageUrl(row);
}

function currentHeroUrl(row: AdminComedianListItem) {
    return row.activeImageAsset?.heroUrl ?? legacyComedianImageUrl(row);
}

function emptyImageDiscoveryState(): ImageDiscoveryState {
    return {
        kind: "idle",
        candidates: [],
        selectedCandidate: null,
        preview: null,
    };
}

function compareByName(a: AdminComedianListItem, b: AdminComedianListItem) {
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
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
    const router = useRouter();
    const [rows, setRows] = useState(comedians);
    const [query, setQuery] = useState("");
    const [sort, setSort] = useState<SortMode>("name-asc");
    const [blockedOnly, setBlockedOnly] = useState(false);
    const [parentOnly, setParentOnly] = useState(false);
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
    const [imageDiscovery, setImageDiscovery] = useState<
        Record<number, ImageDiscoveryState>
    >({});
    const [manualImageUrls, setManualImageUrls] = useState<
        Record<number, ManualImageUrls>
    >({});
    const [pendingId, setPendingId] = useState<number | null>(null);
    const [status, setStatus] = useState<Status>({ kind: "idle" });
    const [isPending, startTransition] = useTransition();

    const visibleRows = useMemo(() => {
        const normalizedQuery = query.trim().toLowerCase();
        const filtered = rows.filter((row) => {
            if (blockedOnly && !row.isBlocked) return false;
            if (parentOnly && row.parent !== null) return false;
            if (normalizedQuery) {
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
            }
            return true;
        });
        return sortRows(filtered, sort);
    }, [blockedOnly, parentOnly, query, rows, sort]);
    const totalPages = Math.max(1, Math.ceil(visibleRows.length / pageSize));
    const currentPage = clampAdminPage(page, totalPages);
    const pageStart = (currentPage - 1) * pageSize;
    const pagedRows = visibleRows.slice(pageStart, pageStart + pageSize);

    useEffect(() => {
        setPage(1);
    }, [blockedOnly, parentOnly, query, sort, pageSize]);

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

    async function saveParent(
        row: AdminComedianListItem,
        parentOverride?: AdminComedianListItem["parent"],
    ) {
        const parent =
            parentOverride === undefined ? parentValue(row) : parentOverride;
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

    function imageState(rowId: number) {
        return imageDiscovery[rowId] ?? emptyImageDiscoveryState();
    }

    function manualImageUrlValue(row: AdminComedianListItem) {
        return (
            manualImageUrls[row.id] ?? {
                headshot: currentAvatarUrl(row),
                hero: currentHeroUrl(row),
            }
        );
    }

    function updateManualImageUrls(
        row: AdminComedianListItem,
        patch: Partial<ManualImageUrls>,
    ) {
        setManualImageUrls((current) => ({
            ...current,
            [row.id]: {
                headshot: manualImageUrlValue(row).headshot,
                hero: manualImageUrlValue(row).hero,
                ...patch,
            },
        }));
    }

    function updateImageState(
        rowId: number,
        updater: (current: ImageDiscoveryState) => ImageDiscoveryState,
    ) {
        setImageDiscovery((current) => ({
            ...current,
            [rowId]: updater(current[rowId] ?? emptyImageDiscoveryState()),
        }));
    }

    async function previewImage(
        row: AdminComedianListItem,
        candidate: ImageCandidate,
    ) {
        setStatus({ kind: "idle" });
        setPendingId(row.id);
        updateImageState(row.id, (current) => ({
            ...current,
            selectedCandidate: candidate,
            preview: null,
            error: undefined,
        }));

        let res: Response;
        try {
            res = await fetch("/api/admin/comedians/images/preview", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    comedianId: row.id,
                    imageUrl: candidate.imageUrl,
                    ...(candidate.heroImageUrl
                        ? { heroImageUrl: candidate.heroImageUrl }
                        : {}),
                    ...(candidate.sourcePage
                        ? { sourcePageUrl: candidate.sourcePage }
                        : {}),
                }),
            });
        } catch (error) {
            setPendingId(null);
            updateImageState(row.id, (current) => ({
                ...current,
                kind: "error",
                error: error instanceof Error ? error.message : "Network error",
            }));
            return;
        }

        setPendingId(null);
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
            updateImageState(row.id, (current) => ({
                ...current,
                kind: "error",
                error: body.error ?? `Request failed (${res.status})`,
            }));
            return;
        }

        updateImageState(row.id, (current) => ({
            ...current,
            kind: "ready",
            selectedCandidate: candidate,
            preview: {
                avatarDataUrl: body.avatarDataUrl,
                heroDataUrl: body.heroDataUrl,
                warnings: body.warnings ?? [],
            },
        }));
    }

    async function validateManualImage(row: AdminComedianListItem) {
        const manualUrls = manualImageUrlValue(row);
        const imageUrl = manualUrls.headshot.trim();
        const heroImageUrl = manualUrls.hero.trim();
        if (!imageUrl || !heroImageUrl) return;

        await previewImage(row, {
            imageUrl,
            heroImageUrl,
            sourcePage: null,
            width: null,
            height: null,
            mimeType: null,
            score: 0,
            reasons: ["manual URL"],
        });
    }

    async function publishImage(row: AdminComedianListItem) {
        const state = imageState(row.id);
        const candidate = state.selectedCandidate;
        if (!candidate || !state.preview) return;

        setStatus({ kind: "idle" });
        setPendingId(row.id);

        let res: Response;
        try {
            res = await fetch("/api/admin/comedians/images/publish", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    comedianId: row.id,
                    imageUrl: candidate.imageUrl,
                    ...(candidate.heroImageUrl
                        ? { heroImageUrl: candidate.heroImageUrl }
                        : {}),
                    ...(candidate.sourcePage
                        ? { sourcePageUrl: candidate.sourcePage }
                        : {}),
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
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
            setStatus({
                kind: "error",
                message: body.error ?? `Request failed (${res.status})`,
            });
            return;
        }

        setRows((current) =>
            current.map((currentRow) =>
                currentRow.id === row.id
                    ? {
                          ...currentRow,
                          hasImage: true,
                          activeImageAsset: {
                              id: body.asset.id,
                              sourceImageUrl: body.asset.sourceImageUrl,
                              avatarPath: body.asset.avatarPath,
                              heroPath: body.asset.heroPath,
                              avatarUrl: body.asset.avatarUrl,
                              heroUrl: body.asset.heroUrl,
                              mimeType: body.asset.mimeType,
                              width: body.asset.width,
                              height: body.asset.height,
                          },
                      }
                    : currentRow,
            ),
        );
        updateImageState(row.id, (current) => ({
            ...current,
            selectedCandidate: null,
            preview: null,
        }));
        setStatus({ kind: "ok", message: `${row.name} image published.` });
        startTransition(() => router.refresh());
    }

    async function removeImage(row: AdminComedianListItem) {
        setStatus({ kind: "idle" });
        setPendingId(row.id);

        let res: Response;
        try {
            res = await fetch("/api/admin/comedians/images", {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ comedianId: row.id }),
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

        setRows((current) =>
            current.map((currentRow) =>
                currentRow.id === row.id
                    ? {
                          ...currentRow,
                          hasImage: false,
                          activeImageAsset: null,
                          legacyImageUrl: "",
                      }
                    : currentRow,
            ),
        );
        setManualImageUrls((current) => {
            const next = { ...current };
            delete next[row.id];
            return next;
        });
        updateImageState(row.id, () => emptyImageDiscoveryState());
        setStatus({ kind: "ok", message: `${row.name} images removed.` });
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
                    <label className="inline-flex h-10 items-center gap-2 rounded-md border border-soft-charcoal/30 bg-white px-3 font-dmSans text-body font-semibold text-cedar">
                        <input
                            type="checkbox"
                            checked={blockedOnly}
                            onChange={(event) =>
                                setBlockedOnly(event.target.checked)
                            }
                            className="h-4 w-4 accent-copper-dark"
                        />
                        Blocked status
                    </label>
                    <label className="inline-flex h-10 items-center gap-2 rounded-md border border-soft-charcoal/30 bg-white px-3 font-dmSans text-body font-semibold text-cedar">
                        <input
                            type="checkbox"
                            checked={parentOnly}
                            onChange={(event) =>
                                setParentOnly(event.target.checked)
                            }
                            className="h-4 w-4 accent-copper-dark"
                        />
                        Is Parent
                    </label>
                </div>
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
                <div className="grid min-w-[1500px] grid-cols-[minmax(340px,1.05fr)_minmax(360px,1fr)_minmax(300px,0.9fr)_minmax(280px,0.75fr)] gap-6 border-b border-copper/20 bg-cedar px-4 py-3 font-dmSans text-caption font-semibold uppercase tracking-wide text-coconut-cream">
                    <div>Comedian</div>
                    <div>Images</div>
                    <div>Parent relationship</div>
                    <div>Blocklist</div>
                </div>
                <ul className="divide-y divide-copper/15">
                    {pagedRows.map((row) => {
                        const parent = parentValue(row);
                        const candidates = parentCandidates(row);
                        const disabled = pendingId !== null || isPending;
                        const podcastsOpen = openPodcastRows.has(row.id);
                        const rowImageState = imageState(row.id);
                        const currentAvatar = currentAvatarUrl(row);
                        const currentHero = currentHeroUrl(row);
                        const legacyAvatar = legacyComedianImageUrl(row);

                        if (row.isBlocked) {
                            return (
                                <li
                                    key={row.id}
                                    className="grid min-w-[1120px] items-start gap-x-6 gap-y-4 px-4 py-5 lg:grid-cols-[minmax(360px,1.15fr)_minmax(320px,0.95fr)_minmax(300px,0.8fr)]"
                                >
                                    <div className="min-w-0 space-y-2">
                                        <h2 className="break-words font-gilroy-bold text-h3 text-cedar">
                                            {row.name}
                                        </h2>
                                        <span className="inline-flex w-fit rounded-full border border-red-700/30 bg-red-50 px-2 py-1 font-dmSans text-caption font-semibold text-red-900">
                                            Blocked
                                        </span>
                                    </div>
                                    <div className="rounded-md border border-red-700/25 bg-red-50 p-3 font-dmSans text-body text-red-950">
                                        <div className="font-semibold">
                                            {row.blockReason ??
                                                "Blocked comedian"}
                                        </div>
                                        <div className="mt-1 text-caption text-red-900">
                                            {row.blockAddedBy ??
                                                "Unknown admin"}
                                            {row.blockAddedAt
                                                ? ` · ${formatDate(row.blockAddedAt)}`
                                                : ""}
                                        </div>
                                    </div>
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="w-fit gap-2 border-green-800/40 bg-white text-green-950 hover:bg-green-50 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                        disabled={
                                            disabled || pendingId === row.id
                                        }
                                        onClick={() =>
                                            void unblockComedian(row)
                                        }
                                    >
                                        <ShieldCheck className="h-4 w-4" />
                                        Remove from blocklist
                                    </Button>
                                </li>
                            );
                        }

                        if (row.parent) {
                            return (
                                <li
                                    key={row.id}
                                    className="grid min-w-[1120px] items-start gap-x-6 gap-y-4 px-4 py-5 lg:grid-cols-[minmax(360px,1.15fr)_minmax(320px,0.95fr)_minmax(300px,0.8fr)]"
                                >
                                    <div className="min-w-0 space-y-2">
                                        <h2 className="break-words font-gilroy-bold text-h3 text-cedar">
                                            {row.name}
                                        </h2>
                                        <span className="inline-flex w-fit rounded-full border border-blue-800/40 bg-blue-50 px-2 py-1 font-dmSans text-caption font-semibold text-blue-950">
                                            Child
                                        </span>
                                    </div>
                                    <div className="rounded-md border border-blue-800/25 bg-blue-50 p-3 font-dmSans text-body text-blue-950">
                                        <div className="font-dmSans text-caption font-semibold uppercase tracking-wide text-blue-900">
                                            Current parent
                                        </div>
                                        <div className="mt-1 font-semibold">
                                            {row.parent.name}
                                        </div>
                                    </div>
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="w-fit gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                        disabled={
                                            disabled || pendingId === row.id
                                        }
                                        onClick={() =>
                                            void saveParent(row, null)
                                        }
                                    >
                                        <X className="h-4 w-4" />
                                        Remove parent relationship
                                    </Button>
                                </li>
                            );
                        }

                        return (
                            <li
                                key={row.id}
                                className="grid min-w-[1500px] items-start gap-x-6 gap-y-4 px-4 py-5 lg:grid-cols-[minmax(340px,1.05fr)_minmax(360px,1fr)_minmax(300px,0.9fr)_minmax(280px,0.75fr)]"
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
                                    <div className="rounded-md border border-copper/20 bg-coconut-cream/35 p-3">
                                        <div className="mb-3">
                                            <div>
                                                <div className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                                    Current image
                                                </div>
                                                <div className="mt-1 font-dmSans text-body font-semibold text-cedar">
                                                    {row.activeImageAsset
                                                        ? "Active asset"
                                                        : row.hasImage
                                                          ? "Legacy fallback"
                                                          : "No current image"}
                                                </div>
                                            </div>
                                        </div>

                                        <div className="mb-3 grid gap-2">
                                            <label className="grid gap-1 font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                                Headshot image URL
                                                <input
                                                    aria-label="Headshot image URL"
                                                    type="url"
                                                    value={
                                                        manualImageUrlValue(row)
                                                            .headshot
                                                    }
                                                    onChange={(event) =>
                                                        updateManualImageUrls(
                                                            row,
                                                            {
                                                                headshot:
                                                                    event.target
                                                                        .value,
                                                            },
                                                        )
                                                    }
                                                    placeholder="https://example.com/headshot.jpg"
                                                    className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                                />
                                            </label>
                                            <label className="grid gap-1 font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                                Hero image URL
                                                <input
                                                    aria-label="Hero image URL"
                                                    type="url"
                                                    value={
                                                        manualImageUrlValue(row)
                                                            .hero
                                                    }
                                                    onChange={(event) =>
                                                        updateManualImageUrls(
                                                            row,
                                                            {
                                                                hero: event
                                                                    .target
                                                                    .value,
                                                            },
                                                        )
                                                    }
                                                    placeholder="https://example.com/hero.jpg"
                                                    className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                                />
                                            </label>
                                            <Button
                                                type="button"
                                                variant="outline"
                                                className="w-fit gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                disabled={
                                                    disabled ||
                                                    !manualImageUrlValue(
                                                        row,
                                                    ).headshot.trim() ||
                                                    !manualImageUrlValue(
                                                        row,
                                                    ).hero.trim()
                                                }
                                                onClick={() =>
                                                    void validateManualImage(
                                                        row,
                                                    )
                                                }
                                            >
                                                <ShieldCheck className="h-4 w-4" />
                                                Validate image URLs
                                            </Button>
                                        </div>

                                        {currentAvatar || currentHero ? (
                                            <div className="flex flex-wrap items-start gap-3">
                                                {currentAvatar ? (
                                                    <div className="space-y-2">
                                                        <img
                                                            src={currentAvatar}
                                                            alt={`${row.name} current headshot image`}
                                                            className="h-24 w-24 rounded-md border border-copper/20 object-cover"
                                                        />
                                                        <div className="font-dmSans text-caption font-semibold text-soft-charcoal">
                                                            Headshot
                                                        </div>
                                                    </div>
                                                ) : null}
                                                {currentHero ? (
                                                    <div className="space-y-2">
                                                        <img
                                                            src={currentHero}
                                                            alt={`${row.name} current hero image`}
                                                            className="h-24 w-40 rounded-md border border-copper/20 object-cover"
                                                        />
                                                        <div className="flex items-center gap-2 font-dmSans text-caption font-semibold text-soft-charcoal">
                                                            Hero
                                                            <a
                                                                href={
                                                                    currentHero
                                                                }
                                                                target="_blank"
                                                                rel="noreferrer"
                                                                className="inline-flex items-center gap-1 text-copper-dark hover:underline"
                                                            >
                                                                Open
                                                                <ExternalLink className="h-3.5 w-3.5" />
                                                            </a>
                                                        </div>
                                                    </div>
                                                ) : null}
                                                {row.activeImageAsset ? (
                                                    <div className="basis-full font-dmSans text-caption text-soft-charcoal">
                                                        Source{" "}
                                                        {formatDimensions(
                                                            row.activeImageAsset
                                                                .width,
                                                            row.activeImageAsset
                                                                .height,
                                                        )}
                                                    </div>
                                                ) : null}
                                            </div>
                                        ) : (
                                            <div className="rounded-md border border-soft-charcoal/20 bg-gray-50 px-3 py-2 font-dmSans text-caption text-soft-charcoal">
                                                No current image
                                            </div>
                                        )}

                                        {legacyAvatar && (
                                            <div className="mt-3 border-t border-copper/15 pt-3">
                                                <div className="mb-2 font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                                    Legacy fallback
                                                </div>
                                                <img
                                                    src={legacyAvatar}
                                                    alt={`${row.name} legacy fallback preview`}
                                                    className="h-[56px] w-[56px] rounded-md border border-copper/20 object-cover"
                                                />
                                            </div>
                                        )}
                                        {row.hasImage && (
                                            <Button
                                                type="button"
                                                variant="outline"
                                                className="mt-3 gap-2 border-red-800/40 bg-white text-red-950 hover:bg-red-50 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                disabled={
                                                    disabled ||
                                                    pendingId === row.id
                                                }
                                                onClick={() =>
                                                    void removeImage(row)
                                                }
                                            >
                                                <Trash2 className="h-4 w-4" />
                                                Remove headshot & hero
                                            </Button>
                                        )}
                                    </div>

                                    {rowImageState.kind === "error" && (
                                        <div className="rounded-md border border-red-700/30 bg-red-50 px-3 py-2 font-dmSans text-caption text-red-900">
                                            {rowImageState.error ??
                                                "Image request failed"}
                                        </div>
                                    )}

                                    {rowImageState.preview && (
                                        <div className="space-y-3 rounded-md border border-copper/20 bg-coconut-cream/35 p-3">
                                            <div className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                                Crop preview
                                            </div>
                                            <div className="flex flex-wrap items-start gap-3">
                                                <div className="space-y-1">
                                                    <img
                                                        src={
                                                            rowImageState
                                                                .preview
                                                                .avatarDataUrl
                                                        }
                                                        alt={`${row.name} avatar crop preview`}
                                                        className="h-24 w-24 rounded-md border border-copper/20 object-cover"
                                                    />
                                                    <div className="font-dmSans text-caption font-semibold text-soft-charcoal">
                                                        Avatar
                                                    </div>
                                                </div>
                                                <div className="space-y-1">
                                                    <img
                                                        src={
                                                            rowImageState
                                                                .preview
                                                                .heroDataUrl
                                                        }
                                                        alt={`${row.name} hero crop preview`}
                                                        className="h-24 w-40 rounded-md border border-copper/20 object-cover"
                                                    />
                                                    <div className="font-dmSans text-caption font-semibold text-soft-charcoal">
                                                        Hero
                                                    </div>
                                                </div>
                                            </div>
                                            {rowImageState.preview.warnings.map(
                                                (warning) => (
                                                    <div
                                                        key={warning}
                                                        className="rounded-md border border-yellow-700/30 bg-yellow-50 px-3 py-2 font-dmSans text-caption text-yellow-950"
                                                    >
                                                        {warning}
                                                    </div>
                                                ),
                                            )}
                                            <Button
                                                type="button"
                                                variant="outline"
                                                className="gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                disabled={disabled}
                                                onClick={() =>
                                                    void publishImage(row)
                                                }
                                            >
                                                <Upload className="h-4 w-4" />
                                                Upload to Bunny CDN
                                            </Button>
                                        </div>
                                    )}
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
                                    className={`lg:col-span-4 ${
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
