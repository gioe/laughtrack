import { db } from "@/lib/db";
import type { Prisma } from "@prisma/client";
import type { PodcastSearchResponse } from "../interface";

const DEFAULT_PAGE_SIZE = 25;
const PUBLIC_PODCAST_OWNERSHIP_WHERE = {
    comedianPodcasts: {
        some: {
            reviewStatus: "accepted",
            associationType: { in: ["host", "owner"] },
        },
    },
} satisfies Prisma.PodcastWhereInput;

function safePodcastImageUrl(url: string | null): string | null {
    return url?.startsWith("https://") ? url : null;
}

function plainText(value: string | null): string | null {
    if (!value) return null;
    const text = value
        .replace(/<[^>]*>/g, " ")
        .replace(/\s+/g, " ")
        .trim();
    return text || null;
}

function containsQuery(query: string) {
    return { contains: query, mode: "insensitive" as const };
}

function normalizePage(raw: string | undefined): number {
    const page = Number(raw);
    if (!Number.isInteger(page) || page < 0) return 0;
    return page;
}

function normalizeSize(raw: string | undefined): number {
    const size = Number(raw);
    if (!Number.isInteger(size) || size < 1) return DEFAULT_PAGE_SIZE;
    return Math.min(size, 50);
}

export async function getSearchedPodcasts(params: {
    q?: string;
    page?: string;
    size?: string;
}): Promise<PodcastSearchResponse> {
    const query = params.q?.trim() ?? "";
    const page = normalizePage(params.page);
    const size = normalizeSize(params.size);
    const where: Prisma.PodcastWhereInput = query
        ? {
              AND: [
                  PUBLIC_PODCAST_OWNERSHIP_WHERE,
                  {
                      OR: [
                          { title: containsQuery(query) },
                          { authorName: containsQuery(query) },
                          { description: containsQuery(query) },
                      ],
                  },
              ],
          }
        : PUBLIC_PODCAST_OWNERSHIP_WHERE;

    const [total, podcasts] = await Promise.all([
        db.podcast.count({ where }),
        db.podcast.findMany({
            where,
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
            orderBy: [{ title: "asc" }, { id: "asc" }],
            take: size,
            skip: page * size,
        }),
    ]);

    return {
        total,
        data: podcasts.map((podcast) => ({
            id: podcast.id,
            slug: podcast.slug,
            title: podcast.title,
            authorName: podcast.authorName,
            websiteUrl: podcast.websiteUrl,
            feedUrl: podcast.feedUrl,
            imageUrl: safePodcastImageUrl(podcast.imageUrl),
            description: plainText(podcast.description),
            episodeCount: podcast._count.episodes,
        })),
    };
}
