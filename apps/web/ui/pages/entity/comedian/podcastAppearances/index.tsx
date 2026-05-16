"use client";

import React from "react";
import { AudioWaveform, ExternalLink, Play } from "lucide-react";
import { ComedianPodcastAppearanceDTO } from "@/objects/class/comedian/podcastAppearance.interface";
import {
    startPodcastEpisode,
    usePodcastPlayer,
} from "@/hooks/usePodcastPlayer";

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

function formatAppearanceRole(role: string): string | null {
    const normalized = role.trim();
    if (!normalized) return null;

    return normalized
        .split(/[-_\s]+/)
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
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

            <ul
                role="list"
                className="divide-y divide-gray-200 border-y border-gray-200"
            >
                {playableAppearances.map((appearance) => {
                    const duration = formatDuration(appearance.durationSeconds);
                    const role = formatAppearanceRole(appearance.appearanceRole);
                    const details = [
                        appearance.podcastName,
                        formatReleaseDate(appearance.releaseDate),
                        duration,
                        role,
                    ].filter(Boolean);
                    const isCurrent =
                        isPlaying && currentEpisode?.id === appearance.id;

                    return (
                        <li
                            key={appearance.id}
                            className="flex items-start justify-between gap-4 py-4 transition-colors hover:bg-coconut-cream/40"
                        >
                            <a
                                href={appearance.episodeUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="group flex min-w-0 flex-1 items-start justify-between gap-4"
                            >
                                <span className="min-w-0">
                                    <span className="block font-gilroy-bold text-base font-bold text-foreground group-hover:text-copper">
                                        {appearance.episodeTitle}
                                    </span>
                                    <span className="mt-1 block font-dmSans text-sm text-gray-600">
                                        {details.join(" · ")}
                                    </span>
                                </span>
                                <ExternalLink
                                    size={18}
                                    className="mt-1 flex-shrink-0 text-gray-400 group-hover:text-copper"
                                    aria-hidden="true"
                                />
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
                                        episodeTitle: appearance.episodeTitle,
                                        episodeUrl: appearance.episodeUrl,
                                        audioUrl: appearance.audioUrl,
                                    })
                                }
                                className="inline-flex flex-none items-center gap-2 rounded-md border border-gray-300 px-3 py-2 font-dmSans text-caption font-semibold text-foreground transition-colors hover:border-copper hover:text-copper focus:outline-none focus:ring-2 focus:ring-copper"
                            >
                                <Play size={16} aria-hidden="true" />
                                <span aria-hidden="true">Play</span>
                                <span className="sr-only">
                                    Play {appearance.episodeTitle}
                                </span>
                            </button>
                        </li>
                    );
                })}
            </ul>
        </section>
    );
};

export default PodcastAppearancesSection;
