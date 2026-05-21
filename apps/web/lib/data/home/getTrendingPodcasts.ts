import zipcodes from "zipcodes";
import { db } from "@/lib/db";
import type { PodcastDTO } from "@/lib/data/podcast/interface";
import { buildPodcastArtworkUrl } from "@/lib/data/podcast/imageUrl";
import type { Prisma } from "@prisma/client";
import { DEFAULT_HOME_RADIUS_MILES } from "@/util/constants/radiusConstants";
import {
    ACCEPTED_PODCAST_COHOST_WHERE,
    ACCEPTED_PODCAST_HOST_WHERE,
    PUBLIC_PODCAST_DENY_LIST_WHERE,
} from "@/lib/data/podcast/publicWhere";

const DEFAULT_LIMIT = 8;
const MAX_LIMIT = 50;

function resolveZipCodes(zipCode: string, radius: number): string[] {
    try {
        const results = zipcodes.radius(zipCode, radius);
        if (!results || results.length === 0) return [zipCode];
        return results.map((z: string | zipcodes.ZipCode) =>
            typeof z === "string" ? z : z.zip,
        );
    } catch {
        return [zipCode];
    }
}

function plainText(value: string | null): string | null {
    if (!value) return null;
    const text = value
        .replace(/<[^>]*>/g, " ")
        .replace(/\s+/g, " ")
        .trim();
    return text || null;
}

function whereFor(
    zipCode: string | null,
    radius: number,
): Prisma.PodcastWhereInput {
    if (!zipCode) {
        return {
            ...PUBLIC_PODCAST_DENY_LIST_WHERE,
            OR: [
                { comedianPodcasts: { some: ACCEPTED_PODCAST_HOST_WHERE } },
                {
                    AND: [
                        {
                            comedianPodcasts: {
                                none: ACCEPTED_PODCAST_HOST_WHERE,
                            },
                        },
                        {
                            comedianPodcasts: {
                                some: ACCEPTED_PODCAST_COHOST_WHERE,
                            },
                        },
                    ],
                },
            ],
        };
    }

    const now = new Date();
    const nearbyZips = resolveZipCodes(zipCode, radius);
    const comedianWhere = {
        parentComedianId: null,
        lineupItems: {
            some: {
                show: {
                    date: { gt: now },
                    club: {
                        zipCode: { in: nearbyZips },
                    },
                },
            },
        },
    } satisfies Prisma.ComedianWhereInput;

    return {
        ...PUBLIC_PODCAST_DENY_LIST_WHERE,
        OR: [
            {
                comedianPodcasts: {
                    some: {
                        ...ACCEPTED_PODCAST_HOST_WHERE,
                        comedian: comedianWhere,
                    },
                },
            },
            {
                AND: [
                    {
                        comedianPodcasts: {
                            none: ACCEPTED_PODCAST_HOST_WHERE,
                        },
                    },
                    {
                        comedianPodcasts: {
                            some: {
                                ...ACCEPTED_PODCAST_COHOST_WHERE,
                                comedian: comedianWhere,
                            },
                        },
                    },
                ],
            },
        ],
    };
}

export async function getTrendingPodcasts(
    zipCode: string | null,
    limit = DEFAULT_LIMIT,
    radius = DEFAULT_HOME_RADIUS_MILES,
): Promise<PodcastDTO[]> {
    const safeLimit = Math.min(Math.max(1, limit), MAX_LIMIT);
    const podcasts = await db.podcast.findMany({
        where: whereFor(zipCode, radius),
        select: {
            id: true,
            slug: true,
            title: true,
            authorName: true,
            websiteUrl: true,
            feedUrl: true,
            imageUrl: true,
            description: true,
            _count: {
                select: {
                    episodes: true,
                },
            },
        },
        orderBy: [
            { favorites: { _count: "desc" } },
            { episodes: { _count: "desc" } },
            { title: "asc" },
            { id: "asc" },
        ],
        take: safeLimit,
    });

    return podcasts.map((podcast) => ({
        id: podcast.id,
        slug: podcast.slug,
        title: podcast.title,
        authorName: podcast.authorName,
        websiteUrl: podcast.websiteUrl,
        feedUrl: podcast.feedUrl,
        imageUrl: buildPodcastArtworkUrl(podcast.imageUrl),
        description: plainText(podcast.description),
        episodeCount: podcast._count.episodes,
    }));
}
