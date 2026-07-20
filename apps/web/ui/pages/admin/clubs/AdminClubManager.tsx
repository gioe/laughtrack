"use client";

import type {
    AdminClubGroup,
    AdminClubListItem,
} from "@/lib/admin/clubManagement";
import {
    AdminPagination,
    AdminSearchField,
    AdminSegmentedControl,
    AdminToolbar,
    clampAdminPage,
} from "@/ui/pages/admin/shared/AdminControls";
import { useEffect, useMemo, useState } from "react";
import {
    AdminClubGroupSection,
    type ClubGroupControls,
    type DisplayClubGroup,
} from "./AdminClubGroupSection";
import {
    AdminClubRowControllerProvider,
    useAdminClubRowStore,
} from "./AdminClubRowController";

type Props = {
    groups: AdminClubGroup[];
};

type GroupView = "chain" | "scraper";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];
const DEFAULT_CHAIN_CONTROLS: ClubGroupControls = {
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

export default function AdminClubManager({ groups }: Props) {
    const [rows, setRows] = useState(groups);
    const [groupView, setGroupView] = useState<GroupView>("chain");
    const [query, setQuery] = useState("");
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(25);
    const [collapsedGroups, setCollapsedGroups] = useState<
        Record<string, boolean>
    >(() => initialCollapsedGroups(groups));
    const [chainControls, setChainControls] = useState<
        Record<string, ClubGroupControls>
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
        patch: Partial<ClubGroupControls>,
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

    const rowStore = useAdminClubRowStore(replaceClub);

    return (
        <AdminClubRowControllerProvider value={rowStore.contextValue}>
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

                {rowStore.status.kind === "ok" && (
                    <p className="rounded-md border border-green-700/30 bg-green-50 px-3 py-2 font-dmSans text-body text-green-900">
                        {rowStore.status.message}
                    </p>
                )}
                {rowStore.status.kind === "error" && (
                    <p className="rounded-md border border-red-700/30 bg-red-50 px-3 py-2 font-dmSans text-body text-red-900">
                        {rowStore.status.message}
                    </p>
                )}

                <AdminPagination
                    page={currentPage}
                    pageSize={pageSize}
                    totalItems={filteredGroups.length}
                    label={
                        groupView === "chain"
                            ? "chain groups"
                            : "scraper groups"
                    }
                    pageSizeOptions={PAGE_SIZE_OPTIONS}
                    onPageChange={(nextPage) =>
                        setPage(clampAdminPage(nextPage, totalPages))
                    }
                    onPageSizeChange={setPageSize}
                />

                <div className="space-y-4">
                    {pagedGroups.map((group) => (
                        <AdminClubGroupSection
                            key={group.key}
                            group={group}
                            collapsed={collapsedGroups[group.key] ?? true}
                            controls={controlsFor(group.key)}
                            clubs={clubsForGroup(group)}
                            onToggle={() => toggleGroup(group.key)}
                            onControlsChange={(patch) =>
                                updateChainControls(group.key, patch)
                            }
                        />
                    ))}
                </div>
                <AdminPagination
                    page={currentPage}
                    pageSize={pageSize}
                    totalItems={filteredGroups.length}
                    label={
                        groupView === "chain"
                            ? "chain groups"
                            : "scraper groups"
                    }
                    pageSizeOptions={PAGE_SIZE_OPTIONS}
                    onPageChange={(nextPage) =>
                        setPage(clampAdminPage(nextPage, totalPages))
                    }
                    onPageSizeChange={setPageSize}
                />
            </div>
        </AdminClubRowControllerProvider>
    );
}
