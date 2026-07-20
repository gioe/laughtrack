"use client";

import type {
    AdminClubGroup,
    AdminClubListItem,
} from "@/lib/admin/clubManagement";
import { validateComedianImageFile } from "@/lib/admin/comedianImageClientValidation";
import { CLUB_TYPE_OPTIONS } from "@/lib/admin/clubTaxonomy";
import { Button } from "@/ui/components/ui/button";
import {
    AdminPagination,
    AdminSearchField,
    AdminSegmentedControl,
    AdminToolbar,
    clampAdminPage,
} from "@/ui/pages/admin/shared/AdminControls";
import { adminRequest } from "../shared/adminRequest";
import {
    ChevronDown,
    ChevronRight,
    ExternalLink,
    Save,
    Trash2,
    Upload,
    X,
} from "lucide-react";
import Link from "next/link";
import type { Dispatch, SetStateAction } from "react";
import { useEffect, useMemo, useState } from "react";

type Props = {
    groups: AdminClubGroup[];
};

type GroupView = "chain" | "scraper";

type DisplayClubGroup = AdminClubGroup & {
    title: string;
    website: string | null;
    grouping: GroupView;
};

type Draft = {
    status: string;
    visible: boolean;
    clubType: string;
    closedAt: string;
};

type Status = {
    kind: "idle" | "ok" | "error";
    message?: string;
};

type ManualClubImage = {
    icon: string;
    iconFile: File | null;
};

type ChainClubControls = {
    query: string;
    sort: string;
    status: string;
    visibility: string;
    clubType: string;
};

const CLUB_STATUS_OPTIONS = ["active", "closed", "hiatus", "not_open_yet"];
const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];
const DEFAULT_CHAIN_CONTROLS: ChainClubControls = {
    query: "",
    sort: "name-asc",
    status: "all",
    visibility: "all",
    clubType: "all",
};

function groupTotals(clubs: AdminClubListItem[]): AdminClubGroup["totals"] {
    return {
        clubCount: clubs.length,
        visibleCount: clubs.filter((club) => club.visible).length,
        activeCount: clubs.filter((club) => club.status === "active").length,
        scrapedShowCount: clubs.reduce(
            (sum, club) => sum + club.scrapedShowCount,
            0,
        ),
    };
}

function flattenUniqueClubs(groups: AdminClubGroup[]) {
    const byId = new Map<number, AdminClubListItem>();
    for (const group of groups) {
        for (const club of group.clubs) byId.set(club.id, club);
    }
    return Array.from(byId.values());
}

function chainDisplayGroups(groups: AdminClubGroup[]): DisplayClubGroup[] {
    return groups.map((group) => ({
        ...group,
        title: group.chain?.name ?? "Unchained",
        website: group.chain?.website ?? null,
        grouping: "chain",
    }));
}

function sourceGroupLabel(
    source: AdminClubListItem["scrapingSources"][number],
) {
    return source.platform === source.scraperKey
        ? source.scraperKey
        : `${source.platform} · ${source.scraperKey}`;
}

function buildScraperDisplayGroups(
    groups: AdminClubGroup[],
): DisplayClubGroup[] {
    const grouped = new Map<
        string,
        {
            title: string;
            clubs: AdminClubListItem[];
        }
    >();

    for (const club of flattenUniqueClubs(groups)) {
        if (club.scrapingSources.length === 0) {
            const key = "scraper-none";
            const entry = grouped.get(key) ?? {
                title: "No scraping source",
                clubs: [],
            };
            entry.clubs.push(club);
            grouped.set(key, entry);
            continue;
        }

        for (const source of club.scrapingSources) {
            const key = `scraper-${source.platform}-${source.scraperKey}`;
            const entry = grouped.get(key) ?? {
                title: sourceGroupLabel(source),
                clubs: [],
            };
            entry.clubs.push(club);
            grouped.set(key, entry);
        }
    }

    return Array.from(grouped.entries())
        .map(([key, group]) => {
            const clubs = sortChainClubs(group.clubs, "name-asc");
            return {
                key,
                chain: null,
                title: group.title,
                website: null,
                grouping: "scraper" as const,
                clubs,
                totals: groupTotals(clubs),
            };
        })
        .sort((a, b) => {
            const countDelta = b.totals.clubCount - a.totals.clubCount;
            if (countDelta !== 0) return countDelta;
            return a.title.localeCompare(b.title, undefined, {
                sensitivity: "base",
            });
        });
}

function dateInputValue(iso: string | null) {
    return iso ? iso.slice(0, 10) : "";
}

function formatDate(iso: string | null) {
    if (!iso) return "Never";
    return iso.replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

function initialDraft(club: AdminClubListItem): Draft {
    return {
        status: club.status,
        visible: club.visible,
        clubType: club.clubType,
        closedAt: dateInputValue(club.closedAt),
    };
}

function isDirty(club: AdminClubListItem, draft: Draft) {
    return (
        draft.status !== club.status ||
        draft.visible !== club.visible ||
        draft.clubType !== club.clubType ||
        draft.closedAt !== dateInputValue(club.closedAt)
    );
}

function statusBadgeClass(club: AdminClubListItem) {
    if (club.status === "closed") {
        return "border-red-700/30 bg-red-50 text-red-900";
    }
    if (club.status === "hiatus") {
        return "border-amber-700/30 bg-amber-50 text-amber-900";
    }
    if (club.status === "not_open_yet") {
        return "border-sky-700/30 bg-sky-50 text-sky-900";
    }
    if (!club.visible) {
        return "border-gray-500/30 bg-gray-100 text-gray-900";
    }
    return "border-green-700/30 bg-green-50 text-green-900";
}

function initialCollapsedGroups(groups: AdminClubGroup[]) {
    return Object.fromEntries(groups.map((group) => [group.key, true]));
}

function compareByName(a: AdminClubListItem, b: AdminClubListItem) {
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
}

function sortChainClubs(clubs: AdminClubListItem[], sort: string) {
    return [...clubs].sort((a, b) => {
        if (sort === "name-desc") return compareByName(b, a);
        if (sort === "shows-desc") {
            return (
                b.scrapedShowCount - a.scrapedShowCount || compareByName(a, b)
            );
        }
        if (sort === "shows-asc") {
            return (
                a.scrapedShowCount - b.scrapedShowCount || compareByName(a, b)
            );
        }
        if (sort === "latest-desc") {
            return (
                new Date(b.latestScrapeAt ?? 0).getTime() -
                    new Date(a.latestScrapeAt ?? 0).getTime() ||
                compareByName(a, b)
            );
        }
        if (sort === "latest-asc") {
            return (
                new Date(a.latestScrapeAt ?? 0).getTime() -
                    new Date(b.latestScrapeAt ?? 0).getTime() ||
                compareByName(a, b)
            );
        }
        return compareByName(a, b);
    });
}

function currentIconUrl(club: AdminClubListItem) {
    return club.activeImageAsset?.iconUrl ?? club.iconUrl;
}

function StagedPreview({
    file,
    alt,
    className,
}: {
    file: File;
    alt: string;
    className: string;
}) {
    const [src, setSrc] = useState<string>("");
    useEffect(() => {
        const url = URL.createObjectURL(file);
        setSrc(url);
        return () => URL.revokeObjectURL(url);
    }, [file]);
    if (!src) return null;
    return <img src={src} alt={alt} className={className} />;
}

export default function AdminClubManager({ groups }: Props) {
    const [rows, setRows] = useState(groups);
    const [groupView, setGroupView] = useState<GroupView>("chain");
    const [query, setQuery] = useState("");
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(25);
    const [drafts, setDrafts] = useState<Record<number, Draft>>({});
    const [nameEdits, setNameEdits] = useState<Record<number, string>>({});
    const [manualImages, setManualImages] = useState<
        Record<number, ManualClubImage>
    >({});
    const [imageStatusByClub, setImageStatusByClub] = useState<
        Record<number, Status>
    >({});
    const [pendingId, setPendingId] = useState<number | null>(null);
    const [status, setStatus] = useState<Status>({ kind: "idle" });
    const [collapsedGroups, setCollapsedGroups] = useState<
        Record<string, boolean>
    >(() => initialCollapsedGroups(groups));
    const [chainControls, setChainControls] = useState<
        Record<string, ChainClubControls>
    >({});

    const activeGroups = useMemo(() => {
        return groupView === "chain"
            ? chainDisplayGroups(rows)
            : buildScraperDisplayGroups(rows);
    }, [groupView, rows]);

    const filteredGroups = useMemo(() => {
        const normalizedQuery = query.trim().toLowerCase();
        if (!normalizedQuery) return activeGroups;
        return activeGroups
            .map((group) => {
                const clubs = group.clubs.filter((club) =>
                    [
                        club.name,
                        club.city ?? "",
                        club.state ?? "",
                        group.title,
                        group.chain?.name ?? "",
                        club.status,
                        club.clubType,
                        club.latestScrapeBy ?? "",
                        ...club.scrapingSources.flatMap((source) => [
                            source.platform,
                            source.scraperKey,
                        ]),
                    ]
                        .join(" ")
                        .toLowerCase()
                        .includes(normalizedQuery),
                );
                return {
                    ...group,
                    clubs,
                    totals: groupTotals(clubs),
                };
            })
            .filter((group) => group.clubs.length > 0);
    }, [activeGroups, query]);

    const flatClubCount = rows.reduce(
        (sum, group) => sum + group.clubs.length,
        0,
    );
    const scrapedShowCount = rows.reduce(
        (sum, group) => sum + group.totals.scrapedShowCount,
        0,
    );
    const totalPages = Math.max(1, Math.ceil(filteredGroups.length / pageSize));
    const currentPage = clampAdminPage(page, totalPages);
    const pagedGroups = filteredGroups.slice(
        (currentPage - 1) * pageSize,
        currentPage * pageSize,
    );

    useEffect(() => {
        setPage(1);
    }, [groupView, query, pageSize]);

    function draftFor(club: AdminClubListItem) {
        return drafts[club.id] ?? initialDraft(club);
    }

    function clubNameValue(club: AdminClubListItem) {
        return Object.hasOwn(nameEdits, club.id)
            ? nameEdits[club.id]
            : club.name;
    }

    function normalizedClubName(name: string) {
        return name.trim().replace(/\s+/g, " ");
    }

    function isNameDirty(club: AdminClubListItem) {
        return normalizedClubName(clubNameValue(club)) !== club.name;
    }

    function updateDraft(club: AdminClubListItem, patch: Partial<Draft>) {
        setDrafts((current) => ({
            ...current,
            [club.id]: {
                ...draftFor(club),
                ...patch,
            },
        }));
    }

    function manualImageValue(club: AdminClubListItem) {
        return (
            manualImages[club.id] ?? {
                icon: currentIconUrl(club),
                iconFile: null,
            }
        );
    }

    function updateManualImage(
        club: AdminClubListItem,
        patch: Partial<ManualClubImage>,
    ) {
        setManualImages((current) => ({
            ...current,
            [club.id]: {
                icon: manualImageValue(club).icon,
                iconFile: manualImageValue(club).iconFile,
                ...patch,
            },
        }));
    }

    function imageHasInput(club: AdminClubListItem) {
        const input = manualImageValue(club);
        return Boolean(
            input.iconFile ||
                (input.icon.trim() &&
                    input.icon.trim() !== currentIconUrl(club)),
        );
    }

    function replaceClub(updated: AdminClubListItem) {
        setRows((current) =>
            current.map((group) => {
                const clubs = group.clubs.map((club) =>
                    club.id === updated.id ? updated : club,
                );
                return {
                    ...group,
                    clubs,
                    totals: {
                        clubCount: clubs.length,
                        visibleCount: clubs.filter((club) => club.visible)
                            .length,
                        activeCount: clubs.filter(
                            (club) => club.status === "active",
                        ).length,
                        scrapedShowCount: clubs.reduce(
                            (sum, club) => sum + club.scrapedShowCount,
                            0,
                        ),
                    },
                };
            }),
        );
    }

    function toggleGroup(groupKey: string) {
        setCollapsedGroups((current) => ({
            ...current,
            [groupKey]: !(current[groupKey] ?? true),
        }));
    }

    function controlsFor(groupKey: string) {
        return chainControls[groupKey] ?? DEFAULT_CHAIN_CONTROLS;
    }

    function updateChainControls(
        groupKey: string,
        patch: Partial<ChainClubControls>,
    ) {
        setChainControls((current) => ({
            ...current,
            [groupKey]: {
                ...DEFAULT_CHAIN_CONTROLS,
                ...current[groupKey],
                ...patch,
            },
        }));
    }

    function clubsForGroup(group: AdminClubGroup) {
        const controls = controlsFor(group.key);
        const normalizedQuery = controls.query.trim().toLowerCase();
        const filtered = group.clubs.filter((club) => {
            if (
                normalizedQuery &&
                ![
                    club.name,
                    club.city ?? "",
                    club.state ?? "",
                    club.status,
                    club.clubType,
                    club.latestScrapeBy ?? "",
                ]
                    .join(" ")
                    .toLowerCase()
                    .includes(normalizedQuery)
            ) {
                return false;
            }
            if (controls.status !== "all" && club.status !== controls.status) {
                return false;
            }
            if (controls.visibility === "visible" && club.visible !== true) {
                return false;
            }
            if (controls.visibility === "blocked" && club.visible !== false) {
                return false;
            }
            if (
                controls.clubType !== "all" &&
                club.clubType !== controls.clubType
            ) {
                return false;
            }
            return true;
        });

        return sortChainClubs(filtered, controls.sort);
    }

    async function saveClub(club: AdminClubListItem) {
        const draft = draftFor(club);
        setStatus({ kind: "idle" });
        setPendingId(club.id);

        let body: { club: AdminClubListItem };
        try {
            body = await adminRequest<{ club: AdminClubListItem }>(
                `/api/admin/clubs/${club.id}`,
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        status: draft.status,
                        visible: draft.visible,
                        clubType: draft.clubType,
                        closedAt: draft.closedAt || null,
                    }),
                },
            );
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
        replaceClub(body.club);
        setDrafts((current) => {
            const next = { ...current };
            delete next[club.id];
            return next;
        });
        setStatus({ kind: "ok", message: `${club.name} saved.` });
    }

    async function saveClubName(club: AdminClubListItem) {
        const name = normalizedClubName(clubNameValue(club));
        if (!name || name === club.name) return;

        setStatus({ kind: "idle" });
        setPendingId(club.id);

        let body: { club: AdminClubListItem };
        try {
            body = await adminRequest<{ club: AdminClubListItem }>(
                `/api/admin/clubs/${club.id}`,
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name }),
                },
            );
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
        replaceClub(body.club);
        setNameEdits((current) => {
            const next = { ...current };
            delete next[club.id];
            return next;
        });
        setStatus({ kind: "ok", message: `${club.name} renamed.` });
    }

    async function stageImageFile(club: AdminClubListItem, file: File) {
        const result = await validateComedianImageFile(file, "headshot");
        if (!result.ok) {
            setStatus({ kind: "error", message: result.reason });
            setImageStatusByClub((current) => ({
                ...current,
                [club.id]: { kind: "error", message: result.reason },
            }));
            return;
        }
        updateManualImage(club, { iconFile: file });
        setStatus({ kind: "idle" });
        setImageStatusByClub((current) => ({
            ...current,
            [club.id]: {
                kind: "ok",
                message: `Thumbnail staged at ${file.name}. Click "Publish to Bunny" to commit, or "Discard" to remove.`,
            },
        }));
    }

    function discardStagedFile(club: AdminClubListItem) {
        updateManualImage(club, { iconFile: null });
        setImageStatusByClub((current) => {
            const next = { ...current };
            delete next[club.id];
            return next;
        });
    }

    async function publishImage(club: AdminClubListItem) {
        const input = manualImageValue(club);
        setStatus({ kind: "idle" });
        setPendingId(club.id);

        let body: { asset: AdminClubListItem["activeImageAsset"] };
        try {
            if (input.iconFile) {
                const formData = new FormData();
                formData.set("clubId", String(club.id));
                formData.set("iconFile", input.iconFile);
                body = await adminRequest<{
                    asset: AdminClubListItem["activeImageAsset"];
                }>("/api/admin/clubs/images/publish", {
                    method: "POST",
                    body: formData,
                });
            } else {
                body = await adminRequest<{
                    asset: AdminClubListItem["activeImageAsset"];
                }>("/api/admin/clubs/images/publish", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        clubId: club.id,
                        iconImageUrl: input.icon.trim(),
                    }),
                });
            }
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
        const asset = body.asset;
        const updated: AdminClubListItem = {
            ...club,
            hasImage: true,
            iconUrl: asset?.iconUrl ?? club.iconUrl,
            heroUrl: asset?.heroUrl ?? club.heroUrl,
            activeImageAsset: asset,
        };
        replaceClub(updated);
        updateManualImage(updated, {
            icon: asset?.iconUrl ?? updated.iconUrl,
            iconFile: null,
        });
        setImageStatusByClub((current) => ({
            ...current,
            [club.id]: {
                kind: "ok",
                message: `${club.name} thumbnail updated.`,
            },
        }));
        setStatus({ kind: "ok", message: `${club.name} thumbnail updated.` });
    }

    async function removeImage(club: AdminClubListItem) {
        setStatus({ kind: "idle" });
        setPendingId(club.id);

        let body: { asset: AdminClubListItem["activeImageAsset"] };
        try {
            body = await adminRequest<{
                asset: AdminClubListItem["activeImageAsset"];
            }>("/api/admin/clubs/images", {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ clubId: club.id }),
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
        const asset = body.asset;
        const updated: AdminClubListItem = {
            ...club,
            hasImage: false,
            iconUrl: "/placeholders/club-placeholder.svg",
            heroUrl: asset?.heroUrl ?? club.heroUrl,
            activeImageAsset: asset,
        };
        replaceClub(updated);
        updateManualImage(updated, { icon: updated.iconUrl, iconFile: null });
        setImageStatusByClub((current) => ({
            ...current,
            [club.id]: {
                kind: "ok",
                message: `${club.name} thumbnail removed.`,
            },
        }));
        setStatus({ kind: "ok", message: `${club.name} thumbnail removed.` });
    }

    return (
        <div className="space-y-5">
            <AdminToolbar>
                <div className="grid gap-3 lg:grid-cols-[minmax(220px,auto)_minmax(260px,1fr)] lg:items-end">
                    <AdminSegmentedControl
                        label="Club view"
                        value={groupView}
                        onChange={setGroupView}
                        options={[
                            { value: "chain", label: "By chain" },
                            { value: "scraper", label: "By scraper" },
                        ]}
                    />
                    <AdminSearchField
                        label="Search clubs"
                        value={query}
                        onChange={setQuery}
                        placeholder="Name, city, chain, scraper, status"
                    />
                </div>
                <div className="font-dmSans text-body text-soft-charcoal">
                    {flatClubCount.toLocaleString()} clubs ·{" "}
                    {scrapedShowCount.toLocaleString()} scraped shows
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
                totalItems={filteredGroups.length}
                label={
                    groupView === "chain" ? "chain groups" : "scraper groups"
                }
                pageSizeOptions={PAGE_SIZE_OPTIONS}
                onPageChange={(nextPage) =>
                    setPage(clampAdminPage(nextPage, totalPages))
                }
                onPageSizeChange={setPageSize}
            />

            <div className="space-y-4">
                {pagedGroups.map((group) => (
                    <ChainGroupSection
                        key={group.key}
                        group={group}
                        collapsed={collapsedGroups[group.key] ?? true}
                        controls={controlsFor(group.key)}
                        clubs={clubsForGroup(group)}
                        pendingId={pendingId}
                        toggleGroup={toggleGroup}
                        updateChainControls={updateChainControls}
                        draftFor={draftFor}
                        updateDraft={updateDraft}
                        clubNameValue={clubNameValue}
                        setNameEdits={setNameEdits}
                        isNameDirty={isNameDirty}
                        normalizedClubName={normalizedClubName}
                        saveClubName={saveClubName}
                        saveClub={saveClub}
                        manualImageValue={manualImageValue}
                        updateManualImage={updateManualImage}
                        imageHasInput={imageHasInput}
                        imageStatusByClub={imageStatusByClub}
                        stageImageFile={stageImageFile}
                        discardStagedFile={discardStagedFile}
                        publishImage={publishImage}
                        removeImage={removeImage}
                    />
                ))}
            </div>
            <AdminPagination
                page={currentPage}
                pageSize={pageSize}
                totalItems={filteredGroups.length}
                label={
                    groupView === "chain" ? "chain groups" : "scraper groups"
                }
                pageSizeOptions={PAGE_SIZE_OPTIONS}
                onPageChange={(nextPage) =>
                    setPage(clampAdminPage(nextPage, totalPages))
                }
                onPageSizeChange={setPageSize}
            />
        </div>
    );
}

function ChainGroupSection({
    group,
    collapsed,
    controls,
    clubs,
    pendingId,
    toggleGroup,
    updateChainControls,
    draftFor,
    updateDraft,
    clubNameValue,
    setNameEdits,
    isNameDirty,
    normalizedClubName,
    saveClubName,
    saveClub,
    manualImageValue,
    updateManualImage,
    imageHasInput,
    imageStatusByClub,
    stageImageFile,
    discardStagedFile,
    publishImage,
    removeImage,
}: {
    group: DisplayClubGroup;
    collapsed: boolean;
    controls: ChainClubControls;
    clubs: AdminClubListItem[];
    pendingId: number | null;
    toggleGroup: (groupKey: string) => void;
    updateChainControls: (
        groupKey: string,
        patch: Partial<ChainClubControls>,
    ) => void;
    draftFor: (club: AdminClubListItem) => Draft;
    updateDraft: (club: AdminClubListItem, patch: Partial<Draft>) => void;
    clubNameValue: (club: AdminClubListItem) => string;
    setNameEdits: Dispatch<SetStateAction<Record<number, string>>>;
    isNameDirty: (club: AdminClubListItem) => boolean;
    normalizedClubName: (name: string) => string;
    saveClubName: (club: AdminClubListItem) => Promise<void>;
    saveClub: (club: AdminClubListItem) => Promise<void>;
    manualImageValue: (club: AdminClubListItem) => ManualClubImage;
    updateManualImage: (
        club: AdminClubListItem,
        patch: Partial<ManualClubImage>,
    ) => void;
    imageHasInput: (club: AdminClubListItem) => boolean;
    imageStatusByClub: Record<number, Status>;
    stageImageFile: (club: AdminClubListItem, file: File) => Promise<void>;
    discardStagedFile: (club: AdminClubListItem) => void;
    publishImage: (club: AdminClubListItem) => Promise<void>;
    removeImage: (club: AdminClubListItem) => Promise<void>;
}) {
    const groupName = group.title;

    return (
        <section className="overflow-hidden rounded-md border border-copper/20 bg-white">
            <header className="border-b border-copper/20 bg-cedar px-4 py-3 text-white">
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <button
                        type="button"
                        aria-expanded={!collapsed}
                        aria-controls={`club-chain-${group.key}`}
                        onClick={() => toggleGroup(group.key)}
                        className="flex min-w-0 items-start gap-3 text-left"
                    >
                        <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-white/30 bg-white/10">
                            {collapsed ? (
                                <ChevronRight className="h-4 w-4" />
                            ) : (
                                <ChevronDown className="h-4 w-4" />
                            )}
                        </span>
                        <span className="min-w-0">
                            <span className="block font-urbanist-bold text-h3 leading-tight">
                                {groupName}
                            </span>
                            <span className="mt-1 block font-dmSans text-caption text-white/85">
                                {group.clubs.length} clubs in this{" "}
                                {group.grouping} group ·{" "}
                                {group.totals.visibleCount} visible ·{" "}
                                {group.totals.activeCount} active ·{" "}
                                {group.totals.scrapedShowCount.toLocaleString()}{" "}
                                scraped shows
                            </span>
                        </span>
                    </button>
                    <div className="flex items-center gap-3 pl-10 md:pl-0">
                        {group.website && (
                            <a
                                href={group.website}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 font-dmSans text-caption font-semibold text-white hover:underline"
                            >
                                Group site
                                <ExternalLink className="h-3.5 w-3.5" />
                            </a>
                        )}
                    </div>
                </div>
            </header>

            <div
                id={`club-chain-${group.key}`}
                hidden={collapsed}
                className={`${collapsed ? "hidden" : ""}`}
            >
                <div className="border-b border-copper/20 bg-ecru-white/70 px-4 py-3">
                    <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_180px_150px_150px_150px] md:items-end">
                        <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                            Search within {groupName}
                            <input
                                aria-label={`Search within ${groupName}`}
                                type="search"
                                value={controls.query}
                                onChange={(event) =>
                                    updateChainControls(group.key, {
                                        query: event.target.value,
                                    })
                                }
                                className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                placeholder="Club, city, status, scraper"
                            />
                        </label>
                        <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                            Sort clubs
                            <select
                                aria-label={`Sort ${groupName} clubs`}
                                value={controls.sort}
                                onChange={(event) =>
                                    updateChainControls(group.key, {
                                        sort: event.target.value,
                                    })
                                }
                                className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                            >
                                <option value="name-asc">Name A-Z</option>
                                <option value="name-desc">Name Z-A</option>
                                <option value="shows-desc">
                                    Scraped shows high-low
                                </option>
                                <option value="shows-asc">
                                    Scraped shows low-high
                                </option>
                                <option value="latest-desc">
                                    Latest scrape newest
                                </option>
                                <option value="latest-asc">
                                    Latest scrape oldest
                                </option>
                            </select>
                        </label>
                        <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                            Status filter
                            <select
                                aria-label={`Filter ${groupName} clubs by status`}
                                value={controls.status}
                                onChange={(event) =>
                                    updateChainControls(group.key, {
                                        status: event.target.value,
                                    })
                                }
                                className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                            >
                                <option value="all">All</option>
                                {CLUB_STATUS_OPTIONS.map((option) => (
                                    <option key={option} value={option}>
                                        {option}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                            Visibility filter
                            <select
                                aria-label={`Filter ${groupName} clubs by visibility`}
                                value={controls.visibility}
                                onChange={(event) =>
                                    updateChainControls(group.key, {
                                        visibility: event.target.value,
                                    })
                                }
                                className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                            >
                                <option value="all">All</option>
                                <option value="visible">Visible</option>
                                <option value="blocked">Blocked</option>
                            </select>
                        </label>
                        <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                            Type filter
                            <select
                                aria-label={`Filter ${groupName} clubs by type`}
                                value={controls.clubType}
                                onChange={(event) =>
                                    updateChainControls(group.key, {
                                        clubType: event.target.value,
                                    })
                                }
                                className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                            >
                                <option value="all">All</option>
                                {CLUB_TYPE_OPTIONS.map((option) => (
                                    <option key={option} value={option}>
                                        {option}
                                    </option>
                                ))}
                            </select>
                        </label>
                    </div>
                    <div className="mt-2 font-dmSans text-caption font-semibold text-soft-charcoal">
                        {clubs.length.toLocaleString()} of{" "}
                        {group.clubs.length.toLocaleString()} clubs shown
                    </div>
                </div>
                <ul className="divide-y divide-copper/15">
                    {clubs.map((club) => {
                        const draft = draftFor(club);
                        const dirty = isDirty(club, draft);
                        const disabled = pendingId !== null;
                        return (
                            <li
                                key={club.id}
                                className="grid gap-4 px-4 py-4 xl:grid-cols-[minmax(260px,0.95fr)_minmax(240px,320px)_minmax(300px,420px)]"
                            >
                                <div className="min-w-0">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <Link
                                            href={`/admin/clubs/${club.id}`}
                                            className="font-urbanist-bold text-h3 text-cedar hover:underline"
                                        >
                                            {club.name}
                                        </Link>
                                        <span
                                            className={`rounded-full border px-2 py-1 font-dmSans text-caption font-semibold ${statusBadgeClass(club)}`}
                                        >
                                            {club.status}
                                        </span>
                                        {!club.visible && (
                                            <span className="rounded-full border border-gray-500/30 bg-gray-100 px-2 py-1 font-dmSans text-caption font-semibold text-gray-900">
                                                Blocked
                                            </span>
                                        )}
                                    </div>
                                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-dmSans text-body text-soft-charcoal">
                                        <span>ID {club.id}</span>
                                        <span>
                                            {[club.city, club.state]
                                                .filter(Boolean)
                                                .join(", ") || "—"}
                                        </span>
                                        <span>{club.clubType}</span>
                                    </div>
                                    <div className="mt-2 flex flex-wrap gap-3 font-dmSans text-caption">
                                        <a
                                            href={club.website}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="inline-flex items-center gap-1 text-copper-dark hover:underline"
                                        >
                                            Website
                                            <ExternalLink className="h-3.5 w-3.5" />
                                        </a>
                                        <Link
                                            href={`/club/${encodeURIComponent(club.name)}`}
                                            target="_blank"
                                            className="text-copper-dark hover:underline"
                                        >
                                            Public page
                                        </Link>
                                    </div>
                                    <div className="mt-3 rounded-md border border-copper/20 bg-coconut-cream/35 p-3">
                                        <label className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                            Display name
                                        </label>
                                        <div className="mt-1 flex items-center gap-2">
                                            <input
                                                aria-label="Club name"
                                                type="text"
                                                value={clubNameValue(club)}
                                                onChange={(event) =>
                                                    setNameEdits((current) => ({
                                                        ...current,
                                                        [club.id]:
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
                                                    pendingId === club.id ||
                                                    !isNameDirty(club) ||
                                                    !normalizedClubName(
                                                        clubNameValue(club),
                                                    )
                                                }
                                                onClick={() =>
                                                    void saveClubName(club)
                                                }
                                            >
                                                <Save className="h-4 w-4" />
                                                Save name
                                            </Button>
                                        </div>
                                    </div>
                                </div>

                                <div className="font-dmSans text-body text-soft-charcoal">
                                    <div>
                                        <span className="font-semibold text-cedar">
                                            Shows scraped:
                                        </span>{" "}
                                        {club.scrapedShowCount.toLocaleString()}
                                    </div>
                                    <div>
                                        <span className="font-semibold text-cedar">
                                            Stored total:
                                        </span>{" "}
                                        {club.totalShows.toLocaleString()}
                                    </div>
                                    <div>
                                        <span className="font-semibold text-cedar">
                                            Latest scrape:
                                        </span>{" "}
                                        {formatDate(club.latestScrapeAt)}
                                        {club.latestScrapeBy
                                            ? ` by ${club.latestScrapeBy}`
                                            : ""}
                                    </div>
                                    <div className="mt-2 flex flex-wrap gap-2">
                                        {club.scrapingSources.length === 0 ? (
                                            <span className="rounded-md border border-amber-700/30 bg-amber-50 px-2 py-1 text-caption font-semibold text-amber-900">
                                                No scraping source
                                            </span>
                                        ) : (
                                            club.scrapingSources.map(
                                                (source) => (
                                                    <span
                                                        key={source.id}
                                                        className={`rounded-md border px-2 py-1 text-caption font-semibold ${
                                                            source.enabled
                                                                ? "border-green-700/30 bg-green-50 text-green-900"
                                                                : "border-gray-500/30 bg-gray-100 text-gray-900"
                                                        }`}
                                                    >
                                                        {source.priority}:{" "}
                                                        {source.platform} ·{" "}
                                                        {source.scraperKey}
                                                    </span>
                                                ),
                                            )
                                        )}
                                    </div>
                                </div>

                                <div className="grid gap-3 md:grid-cols-2">
                                    <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                        Status
                                        <select
                                            value={draft.status}
                                            onChange={(event) =>
                                                updateDraft(club, {
                                                    status: event.target.value,
                                                })
                                            }
                                            className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                                        >
                                            {CLUB_STATUS_OPTIONS.map(
                                                (option) => (
                                                    <option
                                                        key={option}
                                                        value={option}
                                                    >
                                                        {option}
                                                    </option>
                                                ),
                                            )}
                                        </select>
                                    </label>
                                    <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                        Visibility
                                        <select
                                            value={
                                                draft.visible
                                                    ? "visible"
                                                    : "blocked"
                                            }
                                            onChange={(event) =>
                                                updateDraft(club, {
                                                    visible:
                                                        event.target.value ===
                                                        "visible",
                                                })
                                            }
                                            className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                                        >
                                            <option value="visible">
                                                visible
                                            </option>
                                            <option value="blocked">
                                                blocked
                                            </option>
                                        </select>
                                    </label>
                                    <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                        Type
                                        <select
                                            value={draft.clubType}
                                            onChange={(event) =>
                                                updateDraft(club, {
                                                    clubType:
                                                        event.target.value,
                                                })
                                            }
                                            className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                                        >
                                            {CLUB_TYPE_OPTIONS.map((option) => (
                                                <option
                                                    key={option}
                                                    value={option}
                                                >
                                                    {option}
                                                </option>
                                            ))}
                                        </select>
                                    </label>
                                    <label className="grid gap-1 font-dmSans text-body font-semibold text-cedar">
                                        Closed date
                                        <input
                                            type="date"
                                            value={draft.closedAt}
                                            onChange={(event) =>
                                                updateDraft(club, {
                                                    closedAt:
                                                        event.target.value,
                                                })
                                            }
                                            className="rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 text-cedar outline-none focus:border-copper focus:ring-2 focus:ring-copper/30"
                                        />
                                    </label>
                                    <div className="md:col-span-2">
                                        <Button
                                            type="button"
                                            variant="outline"
                                            className="gap-2 border-copper-dark bg-white text-copper-dark disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                            disabled={
                                                disabled ||
                                                !dirty ||
                                                pendingId === club.id
                                            }
                                            onClick={() => void saveClub(club)}
                                        >
                                            <Save className="h-4 w-4" />
                                            Save status override
                                        </Button>
                                    </div>
                                    <div className="space-y-3 rounded-md border border-copper/20 bg-white/80 p-3 md:col-span-2">
                                        <div className="flex items-center justify-between gap-2">
                                            <div className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                                Current image
                                            </div>
                                            {club.hasImage ? (
                                                <a
                                                    href={currentIconUrl(club)}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="inline-flex items-center gap-1 font-dmSans text-caption font-semibold text-copper-dark hover:underline"
                                                >
                                                    Open
                                                    <ExternalLink className="h-3.5 w-3.5" />
                                                </a>
                                            ) : null}
                                        </div>
                                        {club.hasImage ? (
                                            <img
                                                src={currentIconUrl(club)}
                                                alt={`${club.name} current thumbnail image`}
                                                className="h-20 w-20 rounded-md border border-copper/20 object-contain"
                                            />
                                        ) : manualImageValue(club)
                                              .iconFile ? null : (
                                            <div className="flex h-20 w-20 items-center justify-center rounded-md border border-dashed border-soft-charcoal/30 bg-gray-50 font-dmSans text-caption text-soft-charcoal">
                                                Empty
                                            </div>
                                        )}
                                        <div className="grid gap-1">
                                            <label
                                                htmlFor={`club-icon-url-${club.id}`}
                                                className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal"
                                            >
                                                Thumbnail image URL
                                            </label>
                                            <div className="flex flex-wrap gap-2 sm:flex-nowrap">
                                                <input
                                                    id={`club-icon-url-${club.id}`}
                                                    aria-label="Club thumbnail image URL"
                                                    type="url"
                                                    value={
                                                        manualImageValue(club)
                                                            .icon
                                                    }
                                                    onChange={(event) =>
                                                        updateManualImage(
                                                            club,
                                                            {
                                                                icon: event
                                                                    .target
                                                                    .value,
                                                                iconFile: null,
                                                            },
                                                        )
                                                    }
                                                    placeholder="https://example.com/club-logo.png"
                                                    className="w-full min-w-0 flex-1 rounded-md border border-soft-charcoal/30 bg-white px-3 py-2 font-dmSans text-body normal-case tracking-normal text-cedar outline-none placeholder:text-soft-charcoal focus:border-copper focus:ring-2 focus:ring-copper/30"
                                                />
                                                <Button
                                                    type="button"
                                                    variant="outline"
                                                    aria-label="Save club thumbnail URL"
                                                    className="shrink-0 gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                    disabled={
                                                        disabled ||
                                                        pendingId === club.id ||
                                                        !manualImageValue(
                                                            club,
                                                        ).icon.trim() ||
                                                        manualImageValue(
                                                            club,
                                                        ).icon.trim() ===
                                                            currentIconUrl(club)
                                                    }
                                                    onClick={() =>
                                                        void publishImage(club)
                                                    }
                                                >
                                                    <Save className="h-4 w-4" />
                                                    Save URL
                                                </Button>
                                            </div>
                                        </div>
                                        <div className="flex flex-wrap items-center gap-3">
                                            <input
                                                id={`club-icon-file-${club.id}`}
                                                aria-label="Upload club thumbnail file"
                                                type="file"
                                                accept="image/jpeg,image/png,image/webp,image/avif,image/gif"
                                                className="sr-only"
                                                onChange={async (event) => {
                                                    const file =
                                                        event.target
                                                            .files?.[0] ?? null;
                                                    event.target.value = "";
                                                    if (!file) return;
                                                    await stageImageFile(
                                                        club,
                                                        file,
                                                    );
                                                }}
                                            />
                                            <Button
                                                type="button"
                                                variant="outline"
                                                className="gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                disabled={
                                                    disabled ||
                                                    pendingId === club.id
                                                }
                                                onClick={() => {
                                                    const input =
                                                        document.getElementById(
                                                            `club-icon-file-${club.id}`,
                                                        ) as HTMLInputElement | null;
                                                    input?.click();
                                                }}
                                            >
                                                <Upload className="h-4 w-4" />
                                                Choose thumbnail file
                                            </Button>
                                            <span className="font-dmSans text-caption normal-case tracking-normal text-soft-charcoal">
                                                1:1 square, at least 600x600
                                            </span>
                                        </div>
                                        {manualImageValue(club).iconFile ? (
                                            <div className="inline-flex max-w-full flex-wrap items-center gap-3 rounded-md border border-copper/30 bg-coconut-cream/30 p-3">
                                                <StagedPreview
                                                    file={
                                                        manualImageValue(club)
                                                            .iconFile as File
                                                    }
                                                    alt={`${club.name} pending thumbnail`}
                                                    className="h-16 w-16 shrink-0 rounded-md border border-copper/30 object-contain"
                                                />
                                                <div className="grid min-w-[220px] flex-1 gap-2">
                                                    <div>
                                                        <div className="font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                                                            Pending thumbnail
                                                        </div>
                                                        <div className="font-dmSans text-caption text-soft-charcoal">
                                                            Publish the staged
                                                            file or discard it
                                                            before choosing
                                                            another.
                                                        </div>
                                                    </div>
                                                    <div className="flex flex-wrap gap-2">
                                                        <Button
                                                            type="button"
                                                            className="gap-2 bg-copper-dark text-white hover:bg-cedar disabled:bg-gray-300 disabled:text-soft-charcoal disabled:opacity-100"
                                                            disabled={
                                                                disabled ||
                                                                pendingId ===
                                                                    club.id
                                                            }
                                                            onClick={() =>
                                                                void publishImage(
                                                                    club,
                                                                )
                                                            }
                                                        >
                                                            <Upload className="h-4 w-4" />
                                                            Publish to Bunny
                                                        </Button>
                                                        <Button
                                                            type="button"
                                                            variant="outline"
                                                            className="gap-2 border-soft-charcoal/40 bg-white text-cedar hover:bg-gray-50"
                                                            disabled={
                                                                disabled ||
                                                                pendingId ===
                                                                    club.id
                                                            }
                                                            onClick={() =>
                                                                discardStagedFile(
                                                                    club,
                                                                )
                                                            }
                                                        >
                                                            <X className="h-4 w-4" />
                                                            Discard
                                                        </Button>
                                                    </div>
                                                </div>
                                            </div>
                                        ) : null}
                                        {imageStatusByClub[club.id] ? (
                                            <p
                                                className={
                                                    imageStatusByClub[club.id]
                                                        .kind === "error"
                                                        ? "rounded-md border border-red-700/30 bg-red-50 px-3 py-2 font-dmSans text-caption font-semibold text-red-900"
                                                        : "rounded-md border border-green-700/30 bg-green-50 px-3 py-2 font-dmSans text-caption font-semibold text-green-900"
                                                }
                                            >
                                                {
                                                    imageStatusByClub[club.id]
                                                        .message
                                                }
                                            </p>
                                        ) : null}
                                        {club.hasImage ? (
                                            <Button
                                                type="button"
                                                variant="outline"
                                                className="gap-2 border-red-800/40 bg-white text-red-950 hover:bg-red-50 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                                disabled={
                                                    disabled ||
                                                    pendingId === club.id
                                                }
                                                onClick={() =>
                                                    void removeImage(club)
                                                }
                                            >
                                                <Trash2 className="h-4 w-4" />
                                                Remove thumbnail
                                            </Button>
                                        ) : null}
                                        <Button
                                            type="button"
                                            variant="outline"
                                            className="gap-2 border-copper/40 bg-white text-cedar hover:bg-copper/10 disabled:border-soft-charcoal/30 disabled:bg-gray-100 disabled:text-soft-charcoal disabled:opacity-100"
                                            disabled={
                                                disabled ||
                                                pendingId === club.id ||
                                                !imageHasInput(club)
                                            }
                                            onClick={() =>
                                                void publishImage(club)
                                            }
                                        >
                                            <Upload className="h-4 w-4" />
                                            Upload changed image
                                        </Button>
                                    </div>
                                </div>
                            </li>
                        );
                    })}
                </ul>
            </div>
        </section>
    );
}
