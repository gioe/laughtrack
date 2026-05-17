"use client";

import React from "react";
import Image from "next/image";
import { AudioWaveform, Play, Podcast } from "lucide-react";
import { ComedianPodcastAppearanceDTO } from "@/objects/class/comedian/podcastAppearance.interface";
import {
    startPodcastEpisode,
    usePodcastPlayer,
} from "@/hooks/usePodcastPlayer";
import EntityCard from "@/ui/components/cards/entity";

interface PodcastAppearancesSectionProps {
    appearances: ComedianPodcastAppearanceDTO[];
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

function formatAppearanceRole(role: string): "Host" | "Cohost" | "Guest" {
    switch (role.trim().toLowerCase()) {
        case "host":
            return "Host";
        case "cohost":
            return "Cohost";
        default:
            return "Guest";
    }
}

type PlayablePodcastAppearance = ComedianPodcastAppearanceDTO & {
    audioUrl: string;
};

function isPlayableAppearance(
    appearance: ComedianPodcastAppearanceDTO,
): appearance is PlayablePodcastAppearance {
    return Boolean(appearance.audioUrl);
}

const PodcastAppearancesSection = ({
    appearances,
}: PodcastAppearancesSectionProps) => {
    const currentEpisode = usePodcastPlayer((state) => state.currentEpisode);
    const isPlaying = usePodcastPlayer((state) => state.isPlaying);
    const playableAppearances = appearances.filter(isPlayableAppearance);

    if (playableAppearances.length === 0) return null;

    return (
        <section
            aria-labelledby="recent-podcast-appearances-heading"
            className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 pt-8 pb-2"
        >
            <header className="mb-4">
                <h2
                    id="recent-podcast-appearances-heading"
                    className="font-gilroy-bold text-h2 font-bold text-foreground"
                >
                    Recent podcast appearances
                </h2>
            </header>

            <ul role="list" className="space-y-3">
                {playableAppearances.map((appearance) => {
                    const duration = formatDuration(appearance.durationSeconds);
                    const role = formatAppearanceRole(
                        appearance.appearanceRole,
                    );
                    const details = [
                        formatReleaseDate(appearance.releaseDate),
                        duration,
                    ].filter(Boolean);
                    const isCurrent =
                        isPlaying && currentEpisode?.id === appearance.id;

                    return (
                        <li key={appearance.id}>
                            <EntityCard
                                as="article"
                                chrome="warm"
                                className="flex items-start justify-between gap-3 p-4"
                            >
                                <a
                                    href={appearance.episodeUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="group flex min-w-0 flex-1 items-start gap-3 rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
                                >
                                    <span className="relative flex h-10 w-10 flex-none items-center justify-center overflow-hidden rounded-lg bg-muted text-muted-foreground">
                                        {appearance.podcastImageUrl ? (
                                            <Image
                                                src={appearance.podcastImageUrl}
                                                alt={appearance.podcastName}
                                                fill
                                                sizes="40px"
                                                className="object-cover"
                                            />
                                        ) : (
                                            <Podcast
                                                size={20}
                                                aria-hidden="true"
                                            />
                                        )}
                                    </span>
                                    <span className="min-w-0">
                                        <span
                                            data-testid="podcast-appearance-title"
                                            className="block font-gilroy-bold text-body font-bold leading-tight text-foreground line-clamp-2 group-hover:text-copper"
                                        >
                                            {appearance.episodeTitle}
                                        </span>
                                        <span
                                            data-testid="podcast-appearance-name"
                                            className="mt-0.5 block font-dmSans text-xs leading-snug text-gray-500 line-clamp-2"
                                        >
                                            {appearance.podcastName}
                                        </span>
                                        <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 font-dmSans text-caption text-gray-600">
                                            <span>{details.join(" · ")}</span>
                                            {role ? (
                                                <span className="inline-flex items-center rounded-full bg-copper/10 px-2 py-0.5 font-dmSans text-caption font-semibold text-copper">
                                                    {role}
                                                </span>
                                            ) : null}
                                        </span>
                                    </span>
                                </a>
                                {isCurrent ? (
                                    <span
                                        className="mt-2 inline-flex flex-none items-center text-copper motion-safe:animate-pulse"
                                        aria-label="Now playing"
                                    >
                                        <AudioWaveform
                                            size={18}
                                            aria-hidden="true"
                                        />
                                    </span>
                                ) : null}
                                <button
                                    type="button"
                                    onClick={() =>
                                        startPodcastEpisode({
                                            id: appearance.id,
                                            podcastName: appearance.podcastName,
                                            episodeTitle:
                                                appearance.episodeTitle,
                                            episodeUrl: appearance.episodeUrl,
                                            audioUrl: appearance.audioUrl,
                                        })
                                    }
                                    className="inline-flex h-10 flex-none items-center gap-2 rounded-md border border-gray-300 px-3 font-dmSans text-caption font-semibold text-foreground transition-colors hover:border-copper hover:text-copper focus:outline-none focus:ring-2 focus:ring-copper"
                                >
                                    <Play size={16} aria-hidden="true" />
                                    <span aria-hidden="true">Play</span>
                                    <span className="sr-only">
                                        Play {appearance.episodeTitle}
                                    </span>
                                </button>
                            </EntityCard>
                        </li>
                    );
                })}
            </ul>
        </section>
    );
};

export default PodcastAppearancesSection;
