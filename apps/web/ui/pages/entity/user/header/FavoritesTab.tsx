"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { ShowDTO } from "@/objects/class/show/show.interface";
import type { PodcastDTO } from "@/lib/data/podcast/interface";
import ComedianGridCard from "@/ui/components/cards/comedian";
import ClubSearchCard from "@/ui/components/cards/club/search";
import PodcastSearchCard from "@/ui/components/cards/podcast";
import ShowCard from "@/ui/components/cards/show";
import FavoriteSearchableSection from "./FavoriteSearchableSection";

const FAVORITE_SHOWS_PAGE_SIZE = 20;
const FAVORITE_SHOWS_PAGE_KEY = "showsPage";
const SAVED_SHOWS_PAGE_SIZE = 20;
const UPCOMING_SAVED_SHOWS_PAGE_KEY = "upcomingSavedShowsPage";
const PAST_SAVED_SHOWS_PAGE_KEY = "pastSavedShowsPage";

type SavedShowPeriod = "upcoming" | "past";

interface FavoritePodcastApiItem {
    id: number;
    slug: string;
    title: string;
    authorName: string | null;
    websiteUrl: string | null;
    feedUrl: string | null;
    imageUrl: string | null;
    description: string | null;
    episodeCount: number;
    isFavorite?: boolean;
}

const toPodcastDTO = (item: FavoritePodcastApiItem): PodcastDTO => ({
    id: item.id,
    slug: item.slug,
    title: item.title,
    authorName: item.authorName,
    websiteUrl: item.websiteUrl,
    feedUrl: item.feedUrl,
    imageUrl: item.imageUrl,
    description: item.description,
    episodeCount: item.episodeCount,
    hosts: [],
    isFavorite: item.isFavorite ?? true,
});

const comedianMatches = (comedian: ComedianDTO, q: string): boolean =>
    !!comedian.name && comedian.name.toLowerCase().includes(q);

const clubMatches = (club: ClubDTO, q: string): boolean => {
    const name = club.name?.toLowerCase() ?? "";
    const city = club.city?.toLowerCase() ?? "";
    const chain = club.chainName?.toLowerCase() ?? "";
    return name.includes(q) || city.includes(q) || chain.includes(q);
};

const podcastMatches = (podcast: PodcastDTO, q: string): boolean => {
    const title = podcast.title?.toLowerCase() ?? "";
    const author = podcast.authorName?.toLowerCase() ?? "";
    return title.includes(q) || author.includes(q);
};

const showMatches = (show: ShowDTO, q: string): boolean => {
    const name = (show.name ?? "").toLowerCase();
    const club = (show.clubName ?? "").toLowerCase();
    const lineup =
        show.lineup
            ?.map((entry) => entry.name?.toLowerCase() ?? "")
            .join(" ") ?? "";
    return name.includes(q) || club.includes(q) || lineup.includes(q);
};

const pageFromSearchParams = (
    searchParams: ReturnType<typeof useSearchParams>,
    key: string,
): number =>
    Math.max(1, Number.parseInt(searchParams?.get(key) ?? "1", 10) || 1);

const useSavedShows = (period: SavedShowPeriod, page: number) => {
    const [shows, setShows] = useState<ShowDTO[]>([]);
    const [total, setTotal] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        setIsLoading(true);
        setError(null);

        const loadSavedShows = async () => {
            try {
                const response = await fetch(
                    `/api/v1/saved-shows?period=${period}&page=${page}&size=${SAVED_SHOWS_PAGE_SIZE}`,
                    { credentials: "same-origin" },
                );
                if (!response.ok) {
                    throw new Error(`Request failed: ${response.status}`);
                }
                const body = (await response.json()) as {
                    data?: ShowDTO[];
                    total?: number;
                };
                if (!cancelled) {
                    setShows(body.data ?? []);
                    setTotal(body.total ?? 0);
                }
            } catch {
                if (!cancelled) {
                    setShows([]);
                    setTotal(0);
                    setError(`Failed to load ${period} saved shows.`);
                }
            } finally {
                if (!cancelled) setIsLoading(false);
            }
        };

        void loadSavedShows();

        return () => {
            cancelled = true;
        };
    }, [page, period]);

    return { shows, total, isLoading, error };
};

const FavoritesTab = () => {
    const searchParams = useSearchParams();
    const showsPage = pageFromSearchParams(
        searchParams,
        FAVORITE_SHOWS_PAGE_KEY,
    );
    const upcomingSavedShowsPage = pageFromSearchParams(
        searchParams,
        UPCOMING_SAVED_SHOWS_PAGE_KEY,
    );
    const pastSavedShowsPage = pageFromSearchParams(
        searchParams,
        PAST_SAVED_SHOWS_PAGE_KEY,
    );
    const upcomingSavedShows = useSavedShows(
        "upcoming",
        upcomingSavedShowsPage,
    );
    const pastSavedShows = useSavedShows("past", pastSavedShowsPage);

    // A grouped notification tap arrives as ?shows=555,777 — scope the upcoming
    // shows section to just those shows (the notification's context).
    const scopedShowIds = useMemo(() => {
        const raw = searchParams?.get("shows");
        if (!raw) return null;
        const ids = raw
            .split(",")
            .map((value) => Number.parseInt(value, 10))
            .filter((id) => Number.isFinite(id));
        return ids.length ? new Set(ids) : null;
    }, [searchParams]);

    const [comedians, setComedians] = useState<ComedianDTO[]>([]);
    const [clubs, setClubs] = useState<ClubDTO[]>([]);
    const [podcasts, setPodcasts] = useState<PodcastDTO[]>([]);
    const [shows, setShows] = useState<ShowDTO[]>([]);
    const [showsTotal, setShowsTotal] = useState(0);

    const [loadingComedians, setLoadingComedians] = useState(true);
    const [loadingClubs, setLoadingClubs] = useState(true);
    const [loadingPodcasts, setLoadingPodcasts] = useState(true);
    const [loadingShows, setLoadingShows] = useState(true);

    const [comedianError, setComedianError] = useState<string | null>(null);
    const [clubError, setClubError] = useState<string | null>(null);
    const [podcastError, setPodcastError] = useState<string | null>(null);
    const [showError, setShowError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        const fetchJson = async <T,>(
            url: string,
        ): Promise<{ data?: T; total?: number }> => {
            const res = await fetch(url, { credentials: "same-origin" });
            if (!res.ok) {
                throw new Error(`Request failed: ${res.status}`);
            }
            return (await res.json()) as { data?: T; total?: number };
        };

        const loadComedians = async () => {
            try {
                const body =
                    await fetchJson<ComedianDTO[]>("/api/v1/favorites");
                if (!cancelled) setComedians(body.data ?? []);
            } catch {
                if (!cancelled)
                    setComedianError("Failed to load favorite comedians.");
            } finally {
                if (!cancelled) setLoadingComedians(false);
            }
        };
        const loadClubs = async () => {
            try {
                const body = await fetchJson<ClubDTO[]>(
                    "/api/v1/favorite-clubs",
                );
                if (!cancelled) setClubs(body.data ?? []);
            } catch {
                if (!cancelled) setClubError("Failed to load favorite clubs.");
            } finally {
                if (!cancelled) setLoadingClubs(false);
            }
        };
        const loadPodcasts = async () => {
            try {
                const body = await fetchJson<FavoritePodcastApiItem[]>(
                    "/api/v1/favorite-podcasts",
                );
                if (!cancelled)
                    setPodcasts((body.data ?? []).map(toPodcastDTO));
            } catch {
                if (!cancelled)
                    setPodcastError("Failed to load favorite podcasts.");
            } finally {
                if (!cancelled) setLoadingPodcasts(false);
            }
        };

        void Promise.all([loadComedians(), loadClubs(), loadPodcasts()]);

        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        let cancelled = false;
        setLoadingShows(true);
        setShowError(null);

        const loadShows = async () => {
            try {
                const res = await fetch(
                    `/api/v1/favorite-shows?page=${showsPage}&size=${FAVORITE_SHOWS_PAGE_SIZE}`,
                    { credentials: "same-origin" },
                );
                if (!res.ok) {
                    throw new Error(`Request failed: ${res.status}`);
                }
                const body = (await res.json()) as {
                    data?: ShowDTO[];
                    total?: number;
                };
                if (!cancelled) {
                    setShows(body.data ?? []);
                    setShowsTotal(body.total ?? 0);
                }
            } catch {
                if (!cancelled) {
                    setShows([]);
                    setShowsTotal(0);
                    setShowError("Failed to load upcoming shows.");
                }
            } finally {
                if (!cancelled) setLoadingShows(false);
            }
        };

        void loadShows();

        return () => {
            cancelled = true;
        };
    }, [showsPage]);

    const renderComedian = useCallback(
        (comedian: ComedianDTO) => <ComedianGridCard entity={comedian} />,
        [],
    );
    const renderClub = useCallback(
        (club: ClubDTO) => <ClubSearchCard club={club} />,
        [],
    );
    const renderPodcast = useCallback(
        (podcast: PodcastDTO) => <PodcastSearchCard podcast={podcast} />,
        [],
    );
    const renderShow = useCallback(
        (show: ShowDTO) => <ShowCard show={show} />,
        [],
    );
    const renderPastShow = useCallback(
        (show: ShowDTO) => <ShowCard show={show} variant="past" />,
        [],
    );

    const showsHeaderNote =
        !loadingShows && showsTotal > 0
            ? `${showsTotal} upcoming show${showsTotal === 1 ? "" : "s"} from your favorite comedians`
            : undefined;
    const upcomingSavedShowsHeaderNote =
        !upcomingSavedShows.isLoading && upcomingSavedShows.total > 0
            ? `${upcomingSavedShows.total} upcoming saved show${upcomingSavedShows.total === 1 ? "" : "s"}`
            : undefined;
    const pastSavedShowsHeaderNote =
        !pastSavedShows.isLoading && pastSavedShows.total > 0
            ? `${pastSavedShows.total} past saved show${pastSavedShows.total === 1 ? "" : "s"}`
            : undefined;

    return (
        <div className="space-y-12">
            <FavoriteSearchableSection<ComedianDTO>
                title="Saved Comedians"
                items={comedians}
                isLoading={loadingComedians}
                loadError={comedianError}
                emptyMessage="You haven't favorited any comedians yet."
                searchPlaceholder="Search saved comedians"
                matchesQuery={comedianMatches}
                renderItem={renderComedian}
                itemKey={(c) => c.uuid ?? `comedian-${c.id ?? c.name}`}
                gridClassName="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6"
                queryKey="comediansPage"
            />

            <FavoriteSearchableSection<ClubDTO>
                title="Saved Clubs"
                items={clubs}
                isLoading={loadingClubs}
                loadError={clubError}
                emptyMessage="You haven't favorited any clubs yet."
                searchPlaceholder="Search saved clubs"
                matchesQuery={clubMatches}
                renderItem={renderClub}
                itemKey={(c) => c.id ?? `club-${c.name}`}
                gridClassName="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6"
                queryKey="clubsPage"
            />

            <FavoriteSearchableSection<PodcastDTO>
                title="Saved Podcasts"
                items={podcasts}
                isLoading={loadingPodcasts}
                loadError={podcastError}
                emptyMessage="You haven't favorited any podcasts yet."
                searchPlaceholder="Search saved podcasts"
                matchesQuery={podcastMatches}
                renderItem={renderPodcast}
                itemKey={(p) => p.id}
                gridClassName="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6"
                queryKey="podcastsPage"
            />

            <FavoriteSearchableSection<ShowDTO>
                title="Saved Shows — Upcoming"
                items={upcomingSavedShows.shows}
                isLoading={upcomingSavedShows.isLoading}
                loadError={upcomingSavedShows.error}
                emptyMessage="You haven't saved any upcoming shows."
                searchPlaceholder="Search upcoming saved shows"
                matchesQuery={showMatches}
                renderItem={renderShow}
                itemKey={(show) => show.id}
                gridClassName="grid grid-cols-1 gap-4"
                queryKey={UPCOMING_SAVED_SHOWS_PAGE_KEY}
                headerNote={upcomingSavedShowsHeaderNote}
                searchScopeLabel="saved shows"
                serverPageInfo={{
                    currentPage: upcomingSavedShowsPage,
                    pageSize: SAVED_SHOWS_PAGE_SIZE,
                    totalItems: upcomingSavedShows.total,
                }}
            />

            <FavoriteSearchableSection<ShowDTO>
                title="Saved Shows — Past"
                items={pastSavedShows.shows}
                isLoading={pastSavedShows.isLoading}
                loadError={pastSavedShows.error}
                emptyMessage="You haven't saved any past shows."
                searchPlaceholder="Search past saved shows"
                matchesQuery={showMatches}
                renderItem={renderPastShow}
                itemKey={(show) => show.id}
                gridClassName="grid grid-cols-1 gap-4"
                queryKey={PAST_SAVED_SHOWS_PAGE_KEY}
                headerNote={pastSavedShowsHeaderNote}
                searchScopeLabel="saved shows"
                serverPageInfo={{
                    currentPage: pastSavedShowsPage,
                    pageSize: SAVED_SHOWS_PAGE_SIZE,
                    totalItems: pastSavedShows.total,
                }}
            />

            {scopedShowIds && (
                <div className="flex flex-wrap items-center justify-between gap-2 bg-surface-muted border border-subtle rounded-lg px-4 py-3">
                    <span className="text-sm text-foreground/85 font-dmSans">
                        Showing{" "}
                        {shows.filter((s) => scopedShowIds.has(s.id)).length}{" "}
                        {shows.filter((s) => scopedShowIds.has(s.id)).length ===
                        1
                            ? "show"
                            : "shows"}{" "}
                        from your notification
                    </span>
                    <Link
                        href="?tab=favorites"
                        className="text-sm font-semibold text-copper hover:underline"
                    >
                        Show all favorites
                    </Link>
                </div>
            )}

            <FavoriteSearchableSection<ShowDTO>
                title={
                    scopedShowIds
                        ? "From your notification"
                        : "Upcoming Shows from Favorite Comedians"
                }
                items={
                    scopedShowIds
                        ? shows.filter((s) => scopedShowIds.has(s.id))
                        : shows
                }
                isLoading={loadingShows}
                loadError={showError}
                emptyMessage={
                    scopedShowIds
                        ? "Those shows aren't in your upcoming favorites right now."
                        : "No upcoming shows from your favorite comedians."
                }
                searchPlaceholder="Search upcoming shows"
                matchesQuery={showMatches}
                renderItem={renderShow}
                itemKey={(s) => s.id}
                gridClassName="grid grid-cols-1 gap-4"
                queryKey={FAVORITE_SHOWS_PAGE_KEY}
                headerNote={scopedShowIds ? undefined : showsHeaderNote}
                searchScopeLabel="shows"
                serverPageInfo={
                    scopedShowIds
                        ? undefined
                        : {
                              currentPage: showsPage,
                              pageSize: FAVORITE_SHOWS_PAGE_SIZE,
                              totalItems: showsTotal,
                          }
                }
            />
        </div>
    );
};

export default FavoritesTab;
