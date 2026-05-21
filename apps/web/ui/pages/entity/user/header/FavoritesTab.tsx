"use client";

import React, { useCallback, useEffect, useState } from "react";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { ShowDTO } from "@/objects/class/show/show.interface";
import type { PodcastDTO } from "@/lib/data/podcast/interface";
import ComedianGridCard from "@/ui/components/cards/comedian";
import ClubSearchCard from "@/ui/components/cards/club/search";
import PodcastSearchCard from "@/ui/components/cards/podcast";
import ShowCard from "@/ui/components/cards/show";
import FavoriteSearchableSection from "./FavoriteSearchableSection";

interface FavoritesTabProps {
    userId: string;
}

const FAVORITE_SHOWS_PAGE_SIZE = 50;

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

const FavoritesTab = ({ userId: _userId }: FavoritesTabProps) => {
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
                const body = await fetchJson<ComedianDTO[]>("/api/v1/favorites");
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
                const body = await fetchJson<ClubDTO[]>("/api/v1/favorite-clubs");
                if (!cancelled) setClubs(body.data ?? []);
            } catch {
                if (!cancelled) setClubError("Failed to load favorite clubs.");
            } finally {
                if (!cancelled) setLoadingClubs(false);
            }
        };
        const loadPodcasts = async () => {
            try {
                const body = await fetchJson<PodcastDTO[]>(
                    "/api/v1/favorite-podcasts",
                );
                if (!cancelled) setPodcasts(body.data ?? []);
            } catch {
                if (!cancelled)
                    setPodcastError("Failed to load favorite podcasts.");
            } finally {
                if (!cancelled) setLoadingPodcasts(false);
            }
        };
        const loadShows = async () => {
            try {
                const body = await fetchJson<ShowDTO[]>(
                    `/api/v1/favorite-shows?size=${FAVORITE_SHOWS_PAGE_SIZE}`,
                );
                if (!cancelled) {
                    setShows(body.data ?? []);
                    setShowsTotal(body.total ?? 0);
                }
            } catch {
                if (!cancelled)
                    setShowError("Failed to load upcoming shows.");
            } finally {
                if (!cancelled) setLoadingShows(false);
            }
        };

        void Promise.all([
            loadComedians(),
            loadClubs(),
            loadPodcasts(),
            loadShows(),
        ]);

        return () => {
            cancelled = true;
        };
    }, []);

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

    const showsHeaderNote =
        !loadingShows && showsTotal > shows.length
            ? `Showing the next ${shows.length} of ${showsTotal} upcoming shows`
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
                itemKey={(c) => c.uuid ?? c.id ?? c.name ?? ""}
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
                itemKey={(c) => c.id ?? c.name ?? ""}
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
                title="Upcoming Shows from Favorites"
                items={shows}
                isLoading={loadingShows}
                loadError={showError}
                emptyMessage="No upcoming shows from your favorite comedians."
                searchPlaceholder="Search upcoming shows"
                matchesQuery={showMatches}
                renderItem={renderShow}
                itemKey={(s) => s.id}
                gridClassName="grid grid-cols-1 gap-4"
                queryKey="showsPage"
                headerNote={showsHeaderNote}
            />
        </div>
    );
};

export default FavoritesTab;
