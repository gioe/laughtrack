"use client";

import Image from "next/image";
import Link from "next/link";
import { Heart, Podcast } from "lucide-react";
import EntityCard from "@/ui/components/cards/entity";
import { useFavorite } from "@/hooks/useFavorite";
import type { PodcastDTO } from "@/lib/data/podcast/interface";

interface PodcastSearchCardProps {
    podcast: PodcastDTO;
}

export default function PodcastSearchCard({ podcast }: PodcastSearchCardProps) {
    const { isFavorite, handleFavoriteClick, isAuthenticated } = useFavorite({
        initialState: podcast.isFavorite ?? false,
        entityId: String(podcast.id),
        entityType: "podcast",
    });
    const favoriteLabel = isAuthenticated
        ? isFavorite
            ? `Remove ${podcast.title} from favorites`
            : `Add ${podcast.title} to favorites`
        : `Sign in to favorite ${podcast.title}`;

    return (
        <EntityCard chrome="coconut-hover" className="h-full p-4">
            <div className="h-full rounded-lg">
                <span className="relative flex aspect-square w-full items-center justify-center overflow-hidden rounded-xl bg-copper/10 text-copper">
                    <Link
                        href={`/podcast/${podcast.slug}`}
                        className="absolute inset-0 rounded-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
                    >
                        {podcast.imageUrl ? (
                            <Image
                                src={podcast.imageUrl}
                                alt={podcast.title}
                                fill
                                sizes="(max-width: 640px) 100vw, (max-width: 1024px) 33vw, 20vw"
                                className="object-cover"
                            />
                        ) : (
                            <span className="flex h-full w-full items-center justify-center">
                                <Podcast size={36} aria-hidden="true" />
                            </span>
                        )}
                    </Link>
                    <button
                        type="button"
                        onClick={handleFavoriteClick}
                        aria-label={favoriteLabel}
                        aria-pressed={isAuthenticated ? isFavorite : undefined}
                        className={`absolute right-2 top-2 z-10 rounded-full bg-white/90 p-2 text-gray-700 shadow-sm transition hover:bg-white hover:text-red-500 focus:outline-none focus:ring-2 focus:ring-copper ${
                            isAuthenticated
                                ? ""
                                : "border border-dashed border-gray-400"
                        }`}
                    >
                        <Heart
                            aria-hidden="true"
                            className={`h-5 w-5 ${
                                isFavorite ? "fill-current text-red-500" : ""
                            }`}
                        />
                    </button>
                </span>
                <div className="mt-4 min-w-0">
                    <Link
                        href={`/podcast/${podcast.slug}`}
                        className="block rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
                    >
                        <h3 className="font-gilroy-bold text-h3 font-extrabold leading-tight text-foreground line-clamp-2">
                            {podcast.title}
                        </h3>
                    </Link>
                    {podcast.authorName ? (
                        <span className="mt-1 block font-dmSans text-sm text-gray-600 line-clamp-1">
                            {podcast.authorName}
                        </span>
                    ) : null}
                    <span className="mt-3 inline-flex rounded-full bg-copper/10 px-2 py-0.5 font-dmSans text-xs font-semibold text-copper">
                        {podcast.episodeCount} episodes
                    </span>
                </div>
            </div>
        </EntityCard>
    );
}
