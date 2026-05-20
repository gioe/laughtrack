"use client";

import Image from "next/image";
import Link from "next/link";
import { Podcast } from "lucide-react";
import EntityCard from "@/ui/components/cards/entity";
import type { PodcastDTO } from "@/lib/data/podcast/interface";

interface PodcastSearchCardProps {
    podcast: PodcastDTO;
}

export default function PodcastSearchCard({ podcast }: PodcastSearchCardProps) {
    return (
        <EntityCard chrome="coconut-hover" className="h-full p-4">
            <Link
                href={`/podcast/${podcast.slug}`}
                className="block h-full rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
            >
                <span className="relative flex aspect-square w-full items-center justify-center overflow-hidden rounded-xl bg-copper/10 text-copper">
                    {podcast.imageUrl ? (
                        <Image
                            src={podcast.imageUrl}
                            alt={podcast.title}
                            fill
                            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 33vw, 20vw"
                            className="object-cover"
                        />
                    ) : (
                        <Podcast size={36} aria-hidden="true" />
                    )}
                </span>
                <div className="mt-4 min-w-0">
                    <h3 className="font-gilroy-bold text-h3 font-extrabold leading-tight text-foreground line-clamp-2">
                        {podcast.title}
                    </h3>
                    {podcast.authorName ? (
                        <span className="mt-1 block font-dmSans text-sm text-gray-600 line-clamp-1">
                            {podcast.authorName}
                        </span>
                    ) : null}
                    <span className="mt-3 inline-flex rounded-full bg-copper/10 px-2 py-0.5 font-dmSans text-xs font-semibold text-copper">
                        {podcast.episodeCount} episodes
                    </span>
                </div>
            </Link>
        </EntityCard>
    );
}
