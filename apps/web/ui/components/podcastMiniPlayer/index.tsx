"use client";

import React, { useEffect, useRef } from "react";
import { ExternalLink, Pause, Play } from "lucide-react";
import { usePodcastPlayer } from "@/hooks/usePodcastPlayer";

const PodcastMiniPlayer = () => {
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const currentEpisode = usePodcastPlayer((state) => state.currentEpisode);
    const isPlaying = usePodcastPlayer((state) => state.isPlaying);
    const loadError = usePodcastPlayer((state) => state.loadError);
    const play = usePodcastPlayer((state) => state.play);
    const pause = usePodcastPlayer((state) => state.pause);
    const fail = usePodcastPlayer((state) => state.fail);

    useEffect(() => {
        const audio = audioRef.current;
        if (!audio || !currentEpisode) return;

        if (!isPlaying) {
            audio.pause();
            return;
        }

        audio.play().catch(() => fail());
    }, [currentEpisode, fail, isPlaying]);

    if (!currentEpisode) return null;

    const togglePlayback = () => {
        if (isPlaying) {
            pause();
            return;
        }

        play();
    };

    const action = isPlaying ? "Pause" : "Play";

    return (
        <aside
            className="fixed inset-x-0 bottom-0 z-40 border-t border-white/10 bg-coconut-cream/95 px-4 py-3 text-white shadow-2xl backdrop-blur"
            aria-label="Podcast mini-player"
        >
            <div className="mx-auto flex max-w-7xl items-center gap-3">
                <button
                    type="button"
                    onClick={togglePlayback}
                    className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-copper text-white transition-colors hover:bg-copper-bright focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-coconut-cream"
                >
                    {isPlaying ? (
                        <Pause size={20} aria-hidden="true" />
                    ) : (
                        <Play size={20} aria-hidden="true" />
                    )}
                    <span className="sr-only">
                        {action} {currentEpisode.episodeTitle}
                    </span>
                </button>

                <div className="min-w-0 flex-1">
                    <p className="truncate font-gilroy-bold text-sm font-bold text-white">
                        {currentEpisode.episodeTitle}
                    </p>
                    <p className="truncate font-dmSans text-caption text-white/75">
                        {currentEpisode.podcastName}
                    </p>
                    {loadError ? (
                        <p className="mt-1 font-dmSans text-caption text-champagne">
                            Audio unavailable
                        </p>
                    ) : null}
                </div>

                {loadError ? (
                    <a
                        href={currentEpisode.episodeUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex flex-none items-center gap-2 rounded-md border border-white/20 px-3 py-2 font-dmSans text-caption font-semibold text-white transition-colors hover:border-copper hover:text-champagne focus:outline-none focus:ring-2 focus:ring-white"
                    >
                        <ExternalLink size={16} aria-hidden="true" />
                        <span>
                            Open episode page for{" "}
                            {currentEpisode.episodeTitle}
                        </span>
                    </a>
                ) : null}

                <audio
                    ref={audioRef}
                    src={currentEpisode.audioUrl}
                    onError={fail}
                    onEnded={pause}
                    preload="metadata"
                />
            </div>
        </aside>
    );
};

export default PodcastMiniPlayer;
