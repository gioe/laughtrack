"use client";

import Image from "next/image";
import Link from "next/link";
import { ExternalLink, Headphones, Heart, Podcast, Rss } from "lucide-react";
import ComedianGrid from "@/ui/components/grid/comedian";
import EntityCard from "@/ui/components/cards/entity";
import { Button } from "@/ui/components/ui/button";
import { useFavorite } from "@/hooks/useFavorite";
import {
    startPodcastEpisode,
    usePodcastPlayer,
} from "@/hooks/usePodcastPlayer";
import type {
    PodcastDTO,
    PodcastEpisodeDTO,
} from "@/lib/data/podcast/interface";
import type { ComedianDTO } from "@/objects/class/comedian/comedian.interface";

interface PodcastDetailProps {
    podcast: PodcastDTO;
    episodes: PodcastEpisodeDTO[];
    relatedComedians: ComedianDTO[];
}

const DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
});

function formatReleaseDate(date: Date | string | null): string {
    if (!date) return "Release date unavailable";
    return DATE_FORMATTER.format(date instanceof Date ? date : new Date(date));
}

function formatDuration(durationSeconds: number | null): string | null {
    if (!durationSeconds) return null;
    const totalMinutes = Math.floor(durationSeconds / 60);
    if (totalMinutes < 1) return null;
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    const parts = [];
    if (hours > 0) parts.push(`${hours} hr`);
    if (minutes > 0) parts.push(`${minutes} min`);
    return parts.join(" ");
}

function PodcastArtwork({
    podcast,
    sizeClassName,
}: {
    podcast: PodcastDTO;
    sizeClassName: string;
}) {
    return (
        <span
            className={`relative flex shrink-0 items-center justify-center overflow-hidden rounded-xl bg-copper/10 text-copper ${sizeClassName}`}
        >
            {podcast.imageUrl ? (
                <Image
                    src={podcast.imageUrl}
                    alt={podcast.title}
                    fill
                    sizes="(max-width: 768px) 160px, 224px"
                    className="object-cover"
                    priority
                />
            ) : (
                <Podcast size={42} aria-hidden="true" />
            )}
        </span>
    );
}

function EpisodeRow({
    podcast,
    episode,
}: {
    podcast: PodcastDTO;
    episode: PodcastEpisodeDTO;
}) {
    const currentEpisode = usePodcastPlayer((state) => state.currentEpisode);
    const isPlaying = usePodcastPlayer((state) => state.isPlaying);
    const duration = formatDuration(episode.durationSeconds);
    const isCurrent = isPlaying && currentEpisode?.id === episode.id;
    const details = [formatReleaseDate(episode.releaseDate), duration].filter(
        Boolean,
    );
    const audioUrl = episode.audioUrl;

    return (
        <EntityCard
            as="article"
            chrome="warm"
            className="flex items-start justify-between gap-3 p-4"
            ariaLabel={episode.title}
        >
            <a
                href={
                    episode.episodeUrl ??
                    podcast.websiteUrl ??
                    podcast.feedUrl ??
                    "#"
                }
                target="_blank"
                rel="noopener noreferrer"
                className="group flex min-w-0 flex-1 items-start gap-3 rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
            >
                <span className="relative flex h-10 w-10 flex-none items-center justify-center overflow-hidden rounded-lg bg-muted text-muted-foreground">
                    {podcast.imageUrl ? (
                        <Image
                            src={podcast.imageUrl}
                            alt=""
                            fill
                            sizes="40px"
                            className="object-cover"
                        />
                    ) : (
                        <Podcast size={20} aria-hidden="true" />
                    )}
                </span>
                <span className="min-w-0">
                    <span className="block font-gilroy-bold text-body font-bold leading-tight text-foreground line-clamp-2 group-hover:text-copper">
                        {episode.title}
                    </span>
                    <span className="mt-1 block font-dmSans text-caption text-gray-600">
                        {details.join(" · ")}
                    </span>
                    {episode.description ? (
                        <span className="mt-1 block font-dmSans text-xs leading-snug text-gray-500 line-clamp-2">
                            {episode.description}
                        </span>
                    ) : null}
                </span>
            </a>
            {audioUrl ? (
                <button
                    type="button"
                    onClick={() =>
                        startPodcastEpisode({
                            id: episode.id,
                            podcastName: podcast.title,
                            episodeTitle: episode.title,
                            episodeUrl:
                                episode.episodeUrl ??
                                podcast.websiteUrl ??
                                podcast.feedUrl ??
                                "",
                            audioUrl,
                        })
                    }
                    className="inline-flex h-10 flex-none items-center gap-2 rounded-md border border-gray-300 px-3 font-dmSans text-caption font-semibold text-foreground transition-colors hover:border-copper hover:text-copper focus:outline-none focus:ring-2 focus:ring-copper"
                >
                    <Headphones size={16} aria-hidden="true" />
                    <span aria-hidden="true">
                        {isCurrent ? "Playing" : "Play"}
                    </span>
                    <span className="sr-only">
                        {isCurrent ? "Now playing" : "Play"} {episode.title}
                    </span>
                </button>
            ) : null}
        </EntityCard>
    );
}

function PodcastPrimaryCta({ podcast }: { podcast: PodcastDTO }) {
    const websiteUrl = podcast.websiteUrl;
    const feedUrl = podcast.feedUrl;
    const url = websiteUrl ?? feedUrl;
    if (!url) return null;

    const isWebsite = Boolean(websiteUrl);
    const label = isWebsite ? "Listen on host site" : "Open RSS feed";
    const helper = isWebsite
        ? "Opens the podcast's host site in a new tab."
        : "Opens the podcast's RSS feed in a new tab.";

    return (
        <div>
            <Button asChild variant="roundedShimmer" className="gap-2">
                <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`${label} for ${podcast.title}`}
                >
                    {label}
                    <ExternalLink size={16} aria-hidden="true" />
                </a>
            </Button>
            <p className="mt-2 font-dmSans text-xs text-gray-500">{helper}</p>
        </div>
    );
}

export default function PodcastDetail({
    podcast,
    episodes,
    relatedComedians,
}: PodcastDetailProps) {
    const { isFavorite, handleFavoriteClick, isAuthenticated } = useFavorite({
        initialState: podcast.isFavorite ?? false,
        entityId: String(podcast.id),
        entityType: "podcast",
    });
    const favoriteLabel = isAuthenticated
        ? isFavorite
            ? "Remove from favorites"
            : "Add to favorites"
        : "Sign in to favorite this podcast";

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-8 sm:py-10">
            <section className="grid gap-6 md:grid-cols-[224px_minmax(0,1fr)] md:items-end">
                <PodcastArtwork
                    podcast={podcast}
                    sizeClassName="h-40 w-40 sm:h-48 sm:w-48 md:h-56 md:w-56"
                />
                <div className="min-w-0">
                    <p className="font-dmSans text-caption font-bold uppercase tracking-wider text-copper">
                        Podcast
                    </p>
                    <h1 className="mt-2 font-gilroy-bold text-3xl font-bold leading-tight text-foreground sm:text-4xl md:text-h1">
                        {podcast.title}
                    </h1>
                    {podcast.authorName ? (
                        <p className="mt-2 font-dmSans text-lg text-gray-600">
                            Hosted by {podcast.authorName}
                        </p>
                    ) : null}
                    {podcast.description ? (
                        <p className="mt-4 max-w-3xl font-dmSans text-body leading-relaxed text-gray-700 line-clamp-4">
                            {podcast.description}
                        </p>
                    ) : null}
                    <div className="mt-5 flex flex-wrap items-start gap-3">
                        <Button
                            type="button"
                            variant="roundedShimmer"
                            onClick={handleFavoriteClick}
                            aria-label={favoriteLabel}
                            aria-pressed={
                                isAuthenticated ? isFavorite : undefined
                            }
                            className="gap-2"
                        >
                            <Heart
                                size={16}
                                aria-hidden="true"
                                className={
                                    isFavorite
                                        ? "fill-current text-red-100"
                                        : ""
                                }
                            />
                            {isFavorite ? "Favorited" : "Add to favorites"}
                        </Button>
                        <PodcastPrimaryCta podcast={podcast} />
                    </div>
                    <div className="mt-4 flex flex-wrap items-center gap-3">
                        {podcast.websiteUrl && podcast.feedUrl ? (
                            <a
                                href={podcast.feedUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-4 py-2 font-dmSans text-sm font-semibold text-foreground transition-colors hover:border-copper hover:text-copper focus:outline-none focus:ring-2 focus:ring-copper"
                            >
                                RSS
                                <Rss size={16} aria-hidden="true" />
                            </a>
                        ) : null}
                        <span className="font-dmSans text-sm text-gray-600">
                            {podcast.episodeCount} episodes
                        </span>
                    </div>
                </div>
            </section>

            <section
                className="mt-10"
                aria-labelledby="podcast-episodes-heading"
            >
                <h2
                    id="podcast-episodes-heading"
                    className="font-gilroy-bold text-h2 font-bold text-foreground"
                >
                    Episodes
                </h2>
                <ul role="list" className="mt-4 space-y-3">
                    {episodes.map((episode) => (
                        <li key={episode.id}>
                            <EpisodeRow podcast={podcast} episode={episode} />
                        </li>
                    ))}
                </ul>
            </section>

            {relatedComedians.length > 0 ? (
                <section
                    className="mt-12"
                    aria-labelledby="related-comedians-heading"
                >
                    <header className="mb-4 flex items-end justify-between gap-4">
                        <h2
                            id="related-comedians-heading"
                            className="font-gilroy-bold text-h2 font-bold text-foreground"
                        >
                            Related comedians
                        </h2>
                        <Link
                            href="/comedian/search"
                            className="font-dmSans text-sm font-semibold text-copper hover:underline"
                        >
                            Browse comedians
                        </Link>
                    </header>
                    <ComedianGrid
                        comedians={relatedComedians}
                        className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6"
                        cardVariant="compact"
                    />
                </section>
            ) : null}
        </div>
    );
}
