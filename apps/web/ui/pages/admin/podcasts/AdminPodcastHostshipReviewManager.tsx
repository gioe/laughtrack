"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, useTransition } from "react";
import {
    AdminPagination,
    AdminSearchField,
    AdminSegmentedControl,
    AdminSelectField,
    AdminToolbar,
    clampAdminPage,
} from "@/ui/pages/admin/shared/AdminControls";
import type { AdminPodcastHostshipReviewCandidate } from "@/lib/admin/podcastHostshipReviews";
import { adminRequest } from "../shared/adminRequest";
import { AdminPodcastHostshipComedianCard } from "./AdminPodcastHostshipComedianCard";
import { AdminPodcastHostshipPodcastCard } from "./AdminPodcastHostshipPodcastCard";
import type {
    ComedianOption,
    ComedianReviewGroup,
    PodcastReviewGroup,
    SearchResult,
    Status,
} from "./AdminPodcastHostshipReviewModels";

export type { AdminPodcastHostshipReviewCandidate };

type ReviewView = "podcast" | "comedian";
type ReviewSort =
    | "name-asc"
    | "name-desc"
    | "episode-count-desc"
    | "episode-count-asc"
    | "popularity-desc"
    | "popularity-asc";
type ReviewSortOption = { value: ReviewSort; label: string };

type Props = {
    candidates: AdminPodcastHostshipReviewCandidate[];
};

function groupCandidates(
    candidates: AdminPodcastHostshipReviewCandidate[],
): PodcastReviewGroup[] {
    const byPodcast = new Map<number, AdminPodcastHostshipReviewCandidate[]>();
    for (const candidate of candidates) {
        if (!candidate.podcast) continue;
        const rows = byPodcast.get(candidate.podcast.id) ?? [];
        rows.push(candidate);
        byPodcast.set(candidate.podcast.id, rows);
    }

    return Array.from(byPodcast.entries()).map(([podcastId, rows]) => {
        const podcast = rows[0].podcast!;
        const hostshipOptions = rows.flatMap((candidate) =>
            candidate.existingHostships.map((hostship) => ({
                id: hostship.comedian.id,
                uuid: hostship.comedian.uuid,
                name: hostship.comedian.name,
                popularity: hostship.comedian.popularity,
                confidence: hostship.confidence,
                source: hostship.source,
                associationType: hostship.associationType,
                reviewStatus: hostship.reviewStatus,
            })),
        );
        const candidateOptions = rows.map((candidate) => ({
            id: candidate.comedian.id,
            uuid: candidate.comedian.uuid,
            name: candidate.comedian.name,
            popularity: candidate.comedian.popularity,
            confidence: candidate.confidence,
            source: candidate.source,
            associationType: candidate.associationType,
        }));
        const uniqueOptions = new Map<number, ComedianOption>();
        for (const option of [...hostshipOptions, ...candidateOptions]) {
            if (!uniqueOptions.has(option.id))
                uniqueOptions.set(option.id, option);
        }
        const acceptedHost = hostshipOptions.find(
            (option) =>
                option.reviewStatus === "accepted" &&
                option.associationType === "host",
        );
        const acceptedCohosts = hostshipOptions.filter(
            (option) =>
                option.reviewStatus === "accepted" &&
                option.associationType === "cohost",
        );
        const pendingCandidate = rows.find(
            (candidate) => candidate.candidateStatus === "pending",
        );
        const suggestedHost = pendingCandidate
            ? candidateOptions.find(
                  (option) => option.id === pendingCandidate.comedian.id,
              )
            : null;

        return {
            key: String(podcastId),
            podcast,
            candidates: rows,
            comedianOptions: Array.from(uniqueOptions.values()),
            acceptedHost: acceptedHost ?? null,
            acceptedCohosts,
            initialHost: acceptedHost ?? suggestedHost ?? null,
            initialCohosts: acceptedCohosts,
            popularity: Math.max(
                0,
                ...rows.map((candidate) => candidate.comedian.popularity),
                ...hostshipOptions.map((option) => option.popularity),
            ),
        };
    });
}

function groupByComedian(
    candidates: AdminPodcastHostshipReviewCandidate[],
    podcastGroups: PodcastReviewGroup[],
): ComedianReviewGroup[] {
    const podcastGroupById = new Map(
        podcastGroups.map((group) => [group.podcast.id, group]),
    );
    const byComedian = new Map<number, AdminPodcastHostshipReviewCandidate[]>();
    for (const candidate of candidates) {
        if (!candidate.podcast) continue;
        const rows = byComedian.get(candidate.comedian.id) ?? [];
        rows.push(candidate);
        byComedian.set(candidate.comedian.id, rows);
    }

    return Array.from(byComedian.entries()).map(([comedianId, rows]) => {
        const comedian = rows[0].comedian;
        const linkedGroups = rows
            .map((candidate) =>
                candidate.podcast
                    ? podcastGroupById.get(candidate.podcast.id)
                    : undefined,
            )
            .filter((group): group is PodcastReviewGroup => Boolean(group));
        return {
            key: String(comedianId),
            comedian,
            candidates: rows,
            podcastGroups: Array.from(
                new Map(
                    linkedGroups.map((group) => [group.key, group]),
                ).values(),
            ),
            popularity: comedian.popularity,
        };
    });
}

function compareText(a: string, b: string) {
    return a.localeCompare(b, undefined, { sensitivity: "base" });
}

function sortPodcastGroups(groups: PodcastReviewGroup[], sort: ReviewSort) {
    return [...groups].sort((a, b) => {
        switch (sort) {
            case "name-desc":
                return compareText(b.podcast.title, a.podcast.title);
            case "episode-count-desc":
                return (
                    b.podcast.episodeCount - a.podcast.episodeCount ||
                    compareText(a.podcast.title, b.podcast.title)
                );
            case "episode-count-asc":
                return (
                    a.podcast.episodeCount - b.podcast.episodeCount ||
                    compareText(a.podcast.title, b.podcast.title)
                );
            case "popularity-desc":
                return (
                    b.popularity - a.popularity ||
                    compareText(a.podcast.title, b.podcast.title)
                );
            case "popularity-asc":
                return (
                    a.popularity - b.popularity ||
                    compareText(a.podcast.title, b.podcast.title)
                );
            case "name-asc":
            default:
                return compareText(a.podcast.title, b.podcast.title);
        }
    });
}

function sortComedianGroups(groups: ComedianReviewGroup[], sort: ReviewSort) {
    return [...groups].sort((a, b) => {
        switch (sort) {
            case "name-desc":
                return compareText(b.comedian.name, a.comedian.name);
            case "popularity-desc":
                return (
                    b.popularity - a.popularity ||
                    compareText(a.comedian.name, b.comedian.name)
                );
            case "popularity-asc":
                return (
                    a.popularity - b.popularity ||
                    compareText(a.comedian.name, b.comedian.name)
                );
            case "name-asc":
            default:
                return compareText(a.comedian.name, b.comedian.name);
        }
    });
}

function normalizeSearch(value: string) {
    return value.trim().toLocaleLowerCase();
}

function filterPodcastGroups(groups: PodcastReviewGroup[], query: string) {
    const normalizedQuery = normalizeSearch(query);
    if (!normalizedQuery) return groups;

    return groups.filter((group) =>
        group.podcast.title.toLocaleLowerCase().includes(normalizedQuery),
    );
}

function filterComedianGroups(groups: ComedianReviewGroup[], query: string) {
    const normalizedQuery = normalizeSearch(query);
    if (!normalizedQuery) return groups;

    return groups.filter((group) =>
        group.comedian.name.toLocaleLowerCase().includes(normalizedQuery),
    );
}

function selectedHostDefaults(groups: PodcastReviewGroup[]) {
    return Object.fromEntries(
        groups.map((group) => [
            group.key,
            group.podcast.denyListEntry ? null : group.initialHost,
        ]),
    ) as Record<string, ComedianOption | null>;
}

function confirmedHostDefaults(groups: PodcastReviewGroup[]) {
    return Object.fromEntries(
        groups.map((group) => [group.key, group.acceptedHost?.id ?? null]),
    ) as Record<string, number | null>;
}

function selectedCohostDefaults(groups: PodcastReviewGroup[]) {
    return Object.fromEntries(
        groups.map((group) => [
            group.key,
            group.podcast.denyListEntry ? [] : group.initialCohosts,
        ]),
    ) as Record<string, ComedianOption[]>;
}

export default function AdminPodcastHostshipReviewManager({
    candidates,
}: Props) {
    const router = useRouter();
    const groups = useMemo(() => groupCandidates(candidates), [candidates]);
    const comedianGroups = useMemo(
        () => groupByComedian(candidates, groups),
        [candidates, groups],
    );
    const [activeView, setActiveView] = useState<ReviewView>("podcast");
    const [queries, setQueries] = useState<Record<ReviewView, string>>({
        podcast: "",
        comedian: "",
    });
    const [sort, setSort] = useState<ReviewSort>("name-asc");
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(25);
    const [selectedHosts, setSelectedHosts] = useState<
        Record<string, ComedianOption | null>
    >(() => selectedHostDefaults(groups));
    const [selectedCohosts, setSelectedCohosts] = useState<
        Record<string, ComedianOption[]>
    >(() => selectedCohostDefaults(groups));
    const [confirmedHostIds, setConfirmedHostIds] = useState<
        Record<string, number | null>
    >(() => confirmedHostDefaults(groups));
    const [notes, setNotes] = useState<Record<string, string>>({});
    const [searchTerms, setSearchTerms] = useState<Record<string, string>>({});
    const [searchResults, setSearchResults] = useState<
        Record<string, SearchResult[]>
    >({});
    const [manualFeedUrls, setManualFeedUrls] = useState<
        Record<string, string>
    >({});
    const [collapsedGroups, setCollapsedGroups] = useState<
        Record<string, boolean>
    >({});
    const [searchingKey, setSearchingKey] = useState<string | null>(null);
    const [ingestingKey, setIngestingKey] = useState<string | null>(null);
    const [pendingKey, setPendingKey] = useState<string | null>(null);
    const [status, setStatus] = useState<Status>({ kind: "idle" });
    const [isPending, startTransition] = useTransition();
    const activeQuery = queries[activeView];
    const sortOptions: ReviewSortOption[] =
        activeView === "podcast"
            ? [
                  { value: "episode-count-desc", label: "Most Episodes" },
                  { value: "episode-count-asc", label: "Fewest Episodes" },
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
              ]
            : [
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
              ];
    const sortedPodcastGroups = useMemo(
        () =>
            filterPodcastGroups(
                sortPodcastGroups(groups, sort),
                queries.podcast,
            ),
        [groups, queries.podcast, sort],
    );
    const sortedComedianGroups = useMemo(
        () =>
            filterComedianGroups(
                sortComedianGroups(comedianGroups, sort),
                queries.comedian,
            ),
        [comedianGroups, queries.comedian, sort],
    );

    useEffect(() => {
        setPage(1);
    }, [activeView, activeQuery, sort, pageSize]);

    useEffect(() => {
        if (activeView === "comedian" && sort.startsWith("episode-count-")) {
            setSort("name-asc");
        }
    }, [activeView, sort]);

    function updateActiveQuery(value: string) {
        setQueries((current) => ({
            ...current,
            [activeView]: value,
        }));
    }

    function isGroupCollapsed(groupKey: string) {
        return collapsedGroups[groupKey] ?? true;
    }

    function toggleGroup(groupKey: string) {
        setCollapsedGroups((current) => ({
            ...current,
            [groupKey]: !(current[groupKey] ?? true),
        }));
    }

    function selectHost(groupKey: string, option: ComedianOption) {
        setSelectedHosts((prev) => ({
            ...prev,
            [groupKey]: option,
        }));
        setSelectedCohosts((prev) => ({
            ...prev,
            [groupKey]: (prev[groupKey] ?? []).filter(
                (cohost) => cohost.id !== option.id,
            ),
        }));
    }

    function toggleCohost(
        groupKey: string,
        option: ComedianOption,
        isCohost: boolean,
    ) {
        setSelectedCohosts((prev) => {
            const current = prev[groupKey] ?? [];
            const next = isCohost
                ? current.filter((cohost) => cohost.id !== option.id)
                : [
                      ...current.filter((cohost) => cohost.id !== option.id),
                      option,
                  ];
            return {
                ...prev,
                [groupKey]: next,
            };
        });
        if (!isCohost) {
            setSelectedHosts((prev) =>
                prev[groupKey]?.id === option.id
                    ? {
                          ...prev,
                          [groupKey]: null,
                      }
                    : prev,
            );
        }
    }

    async function searchComedians(groupKey: string) {
        const term = searchTerms[groupKey]?.trim();
        if (!term) {
            setSearchResults((prev) => ({ ...prev, [groupKey]: [] }));
            return;
        }

        setSearchingKey(groupKey);
        setStatus({ kind: "idle" });
        try {
            const params = new URLSearchParams({
                comedian: term,
                includeEmpty: "true",
                size: "6",
            });
            const res = await fetch(`/api/v1/comedians/search?${params}`);
            if (!res.ok) throw new Error(`Search failed (${res.status})`);
            const body = (await res.json()) as { data?: SearchResult[] };
            setSearchResults((prev) => ({
                ...prev,
                [groupKey]: (body.data ?? []).map((result) => ({
                    ...result,
                    popularity: result.popularity ?? 0,
                })),
            }));
        } catch (error) {
            setStatus({
                kind: "error",
                message:
                    error instanceof Error ? error.message : "Search failed",
            });
        } finally {
            setSearchingKey(null);
        }
    }

    async function save(
        group: PodcastReviewGroup,
        hostOverride?: ComedianOption | null,
        denyListed?: boolean,
    ) {
        const reason = notes[group.key]?.trim() ?? "";
        const host =
            hostOverride === undefined
                ? (selectedHosts[group.key] ?? null)
                : hostOverride;
        const cohosts =
            hostOverride === null
                ? []
                : (selectedCohosts[group.key] ?? []).filter(
                      (cohost) => cohost.id !== host?.id,
                  );
        const effectiveDenyListed =
            denyListed ?? (host === null && cohosts.length === 0);
        setStatus({ kind: "idle" });
        setPendingKey(group.key);

        try {
            await adminRequest("/api/admin/podcast-hostship-reviews", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    podcastId: group.podcast.id,
                    hostComedianIds: host ? [host.id] : [],
                    cohostComedianIds: cohosts.map((cohost) => cohost.id),
                    denyListed: effectiveDenyListed,
                    reason,
                }),
            });
        } catch (error) {
            setPendingKey(null);
            setStatus({
                kind: "error",
                message:
                    error instanceof Error ? error.message : "Network error",
            });
            return;
        }

        setPendingKey(null);
        setStatus({
            kind: "ok",
            message: effectiveDenyListed
                ? `${group.podcast.title} rejected and deny-listed.`
                : host === null
                  ? cohosts.length > 0
                      ? `${group.podcast.title} approved with co-host only.`
                      : `${group.podcast.title} restored without a host.`
                  : `${group.podcast.title} approved with ${host.name} as host.`,
        });
        setSelectedHosts((prev) => ({
            ...prev,
            [group.key]: host,
        }));
        setConfirmedHostIds((prev) => ({
            ...prev,
            [group.key]: host?.id ?? null,
        }));
        setSelectedCohosts((prev) => ({
            ...prev,
            [group.key]: cohosts,
        }));
        startTransition(() => router.refresh());
    }

    async function ingestManualFeed(comedianGroup: ComedianReviewGroup) {
        const feedUrl = manualFeedUrls[comedianGroup.key]?.trim() ?? "";
        if (!feedUrl) return;

        setStatus({ kind: "idle" });
        setIngestingKey(comedianGroup.key);

        let body: {
            podcast?: { title?: string };
            episodeCount?: number;
        };
        try {
            body = await adminRequest<{
                podcast?: { title?: string };
                episodeCount?: number;
            }>("/api/admin/podcast-hostship-reviews", {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    comedianId: comedianGroup.comedian.id,
                    feedUrl,
                    reason: `Manual RSS feed added during podcast hostship review for ${comedianGroup.comedian.name}`,
                }),
            });
        } catch (error) {
            setIngestingKey(null);
            setStatus({
                kind: "error",
                message:
                    error instanceof Error ? error.message : "Network error",
            });
            return;
        }

        setIngestingKey(null);
        setManualFeedUrls((prev) => ({ ...prev, [comedianGroup.key]: "" }));
        setStatus({
            kind: "ok",
            message: `${body.podcast?.title ?? "RSS feed"} ingested with ${body.episodeCount ?? 0} episodes.`,
        });
        startTransition(() => router.refresh());
    }

    if (groups.length === 0) {
        return (
            <div className="rounded-md border border-copper/20 bg-surface-elevated p-6 font-dmSans text-body text-muted-foreground">
                No podcast hostship review records found.
            </div>
        );
    }

    const activeGroups =
        activeView === "podcast" ? sortedPodcastGroups : sortedComedianGroups;
    const totalPages = Math.max(1, Math.ceil(activeGroups.length / pageSize));
    const currentPage = clampAdminPage(page, totalPages);
    const pageStart = (currentPage - 1) * pageSize;
    const pagedPodcastGroups =
        activeView === "podcast"
            ? sortedPodcastGroups.slice(pageStart, pageStart + pageSize)
            : [];
    const pagedComedianGroups =
        activeView === "comedian"
            ? sortedComedianGroups.slice(pageStart, pageStart + pageSize)
            : [];

    return (
        <div className="space-y-5">
            {status.kind === "ok" && (
                <p className="rounded-md border border-green-200 bg-green-50 px-4 py-3 font-dmSans text-sm text-green-800">
                    {status.message}
                </p>
            )}
            {status.kind === "error" && (
                <p className="rounded-md border border-red-200 bg-red-50 px-4 py-3 font-dmSans text-sm text-red-800">
                    {status.message}
                </p>
            )}
            <AdminToolbar>
                <div className="grid gap-3 lg:grid-cols-[minmax(220px,auto)_minmax(260px,1fr)] lg:items-end">
                    <AdminSegmentedControl
                        label="Review view"
                        value={activeView}
                        onChange={setActiveView}
                        options={[
                            { value: "podcast", label: "By podcast" },
                            { value: "comedian", label: "By comedian" },
                        ]}
                    />
                    <AdminSearchField
                        label={
                            activeView === "podcast"
                                ? "Search podcasts"
                                : "Search comedians"
                        }
                        value={activeQuery}
                        onChange={updateActiveQuery}
                        placeholder={
                            activeView === "podcast"
                                ? "Podcast name"
                                : "Comedian name"
                        }
                    />
                </div>
                <AdminSelectField
                    label="Sort"
                    value={sort}
                    onChange={setSort}
                    options={sortOptions}
                />
            </AdminToolbar>
            <AdminPagination
                page={currentPage}
                pageSize={pageSize}
                totalItems={activeGroups.length}
                label={activeView === "podcast" ? "podcasts" : "comedians"}
                onPageChange={(nextPage) =>
                    setPage(clampAdminPage(nextPage, totalPages))
                }
                onPageSizeChange={setPageSize}
            />
            <div className="space-y-4">
                {activeView === "podcast"
                    ? pagedPodcastGroups.map((group) => (
                          <AdminPodcastHostshipPodcastCard
                              key={group.key}
                              group={group}
                              selectedHost={selectedHosts[group.key] ?? null}
                              selectedCohosts={selectedCohosts[group.key] ?? []}
                              note={notes[group.key] ?? ""}
                              searchTerm={searchTerms[group.key] ?? ""}
                              searchResults={searchResults[group.key] ?? []}
                              collapsed={isGroupCollapsed(
                                  "podcast-" + group.key,
                              )}
                              disabled={isPending || pendingKey !== null}
                              searching={searchingKey === group.key}
                              onToggle={toggleGroup}
                              onSelectHost={selectHost}
                              onRemoveHost={(groupKey) =>
                                  setSelectedHosts((current) => ({
                                      ...current,
                                      [groupKey]: null,
                                  }))
                              }
                              onToggleCohost={toggleCohost}
                              onNoteChange={(groupKey, value) =>
                                  setNotes((current) => ({
                                      ...current,
                                      [groupKey]: value,
                                  }))
                              }
                              onSearchTermChange={(groupKey, value) =>
                                  setSearchTerms((current) => ({
                                      ...current,
                                      [groupKey]: value,
                                  }))
                              }
                              onSearch={searchComedians}
                              onSave={save}
                          />
                      ))
                    : pagedComedianGroups.map((group) => (
                          <AdminPodcastHostshipComedianCard
                              key={group.key}
                              group={group}
                              selectedHosts={selectedHosts}
                              selectedCohosts={selectedCohosts}
                              confirmedHostIds={confirmedHostIds}
                              manualFeedUrl={manualFeedUrls[group.key] ?? ""}
                              collapsed={isGroupCollapsed(
                                  "comedian-" + group.key,
                              )}
                              busy={isPending || pendingKey !== null}
                              ingestDisabled={
                                  ingestingKey !== null || pendingKey !== null
                              }
                              ingesting={ingestingKey === group.key}
                              onToggle={toggleGroup}
                              onManualFeedUrlChange={(value) =>
                                  setManualFeedUrls((current) => ({
                                      ...current,
                                      [group.key]: value,
                                  }))
                              }
                              onIngest={ingestManualFeed}
                              onSelectHost={selectHost}
                              onRemoveHost={(groupKey) =>
                                  setSelectedHosts((current) => ({
                                      ...current,
                                      [groupKey]: null,
                                  }))
                              }
                              onToggleCohost={toggleCohost}
                              onSave={save}
                          />
                      ))}
            </div>
            <AdminPagination
                page={currentPage}
                pageSize={pageSize}
                totalItems={activeGroups.length}
                label={activeView === "podcast" ? "podcasts" : "comedians"}
                onPageChange={(nextPage) =>
                    setPage(clampAdminPage(nextPage, totalPages))
                }
                onPageSizeChange={setPageSize}
            />
        </div>
    );
}
