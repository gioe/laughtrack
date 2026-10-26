"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Play, Podcast } from "lucide-react";
import type { PodcastDiscoverySnapshot } from "@/lib/data/home/podcastDiscoverySnapshot";
import { startPodcastEpisode } from "@/hooks/usePodcastPlayer";

export default function PodcastDiscoveryRail() {
    const container = useRef<HTMLElement>(null);
    const [snapshot, setSnapshot] = useState<PodcastDiscoverySnapshot | null>(
        null,
    );
    const [settled, setSettled] = useState(false);

    useEffect(() => {
        const controller = new AbortController();
        let started = false;
        const load = async () => {
            if (started) return;
            started = true;
            try {
                const response = await fetch("/api/v1/home/podcast-discovery", {
                    signal: controller.signal,
                });
                if (!response.ok) return;
                const result = await response.json();
                if (
                    !controller.signal.aborted &&
                    Array.isArray(result.data?.episodes)
                ) {
                    setSnapshot(result.data);
                }
            } catch {
                // An optional rail must never replace the main feed with an error.
            } finally {
                if (!controller.signal.aborted) setSettled(true);
            }
        };
        // Start only after hydration and as this below-the-fold section approaches.
        const observer = new IntersectionObserver(
            (entries) => {
                if (entries.some((entry) => entry.isIntersecting)) {
                    observer.disconnect();
                    void load();
                }
            },
            { rootMargin: "400px" },
        );
        if (container.current) observer.observe(container.current);
        return () => {
            observer.disconnect();
            controller.abort();
        };
    }, []);

    if (settled && !snapshot?.episodes.length) return null;

    return (
        <section
            ref={container}
            aria-labelledby="podcast-discovery-title"
            className="w-full bg-coconut-cream px-4 py-10 sm:px-6 md:px-8 lg:px-12"
            data-testid="podcast-discovery-rail"
        >
            <div className="mx-auto max-w-6xl">
                <p className="font-dmSans text-sm font-semibold text-copper">
                    Funny listening
                </p>
                <h2
                    id="podcast-discovery-title"
                    className="mt-1 font-urbanist-bold text-3xl text-foreground"
                >
                    Hear a new comedian
                </h2>
                <p className="mt-2 font-dmSans text-muted-foreground">
                    Discover your next favorite through a good conversation.
                </p>
                {!snapshot ? (
                    <div
                        className="mt-6 h-80 rounded-xl bg-surface-muted motion-safe:animate-pulse"
                        role="status"
                        aria-label="Loading podcast episodes"
                    />
                ) : (
                    <ul className="mt-6 space-y-3">
                        {snapshot.episodes.slice(0, 5).map((episode) => {
                            const comedian = episode.recommendation.comedian;
                            const href = `/podcast/${episode.podcast.slug}`;
                            return (
                                <li
                                    key={episode.id}
                                    className="flex items-center gap-4 rounded-xl border border-subtle bg-surface p-4"
                                >
                                    <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-surface-muted">
                                        {episode.podcast.imageUrl ? (
                                            <Image
                                                src={episode.podcast.imageUrl}
                                                alt=""
                                                fill
                                                sizes="64px"
                                                loading="lazy"
                                                className="object-cover"
                                            />
                                        ) : (
                                            <Podcast
                                                className="m-4 h-8 w-8 text-copper"
                                                aria-hidden="true"
                                            />
                                        )}
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <Link
                                            prefetch={false}
                                            href={`/comedian/${encodeURIComponent(comedian.name)}`}
                                            className="font-dmSans font-semibold text-copper hover:underline"
                                        >
                                            {comedian.name}
                                        </Link>
                                        <p className="text-sm text-muted-foreground">
                                            {episode.recommendation
                                                .appearanceRole === "guest"
                                                ? "Guest on"
                                                : "Host on"}{" "}
                                            {episode.podcast.title}
                                        </p>
                                        <Link
                                            prefetch={false}
                                            href={href}
                                            className="mt-1 block font-urbanist-bold text-lg text-foreground hover:underline"
                                        >
                                            {episode.title}
                                        </Link>
                                    </div>
                                    {episode.audioUrl && (
                                        <button
                                            type="button"
                                            aria-label={`Play ${episode.title}`}
                                            onClick={() =>
                                                startPodcastEpisode({
                                                    id: episode.id,
                                                    podcastName:
                                                        episode.podcast.title,
                                                    episodeTitle: episode.title,
                                                    episodeUrl: href,
                                                    audioUrl: episode.audioUrl!,
                                                })
                                            }
                                            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-copper text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
                                        >
                                            <Play
                                                size={20}
                                                aria-hidden="true"
                                            />
                                        </button>
                                    )}
                                </li>
                            );
                        })}
                    </ul>
                )}
            </div>
        </section>
    );
}
