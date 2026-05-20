import { db } from "@/lib/db";
import type { Prisma } from "@prisma/client";
import type { PodcastSearchResponse } from "../interface";
import { buildPodcastArtworkUrl } from "@/lib/data/podcast/imageUrl";

const DEFAULT_PAGE_SIZE = 20;
const PUBLIC_PODCAST_OWNERSHIP_WHERE = {
    comedianPodcasts: {
        some: {
            reviewStatus: "accepted",
            associationType: { in: ["host", "owner"] },
        },
    },
} satisfies Prisma.PodcastWhereInput;

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

// show_count_* are the canonical podcast sort values (web's getSortOptions
// labels them "Most Episodes" / "Fewest Episodes"). popularity_* are kept as
// synonyms because earlier iOS clients shipped them; both map to episode count.
// activity_* and inserted_at_* round out the full web-exposed sort surface.
const PODCAST_SORTS = [
    "show_count_desc",
    "show_count_asc",
    "popularity_desc",
    "popularity_asc",
    "name_asc",
    "name_desc",
    "activity_desc",
    "activity_asc",
    "inserted_at_desc",
    "inserted_at_asc",
] as const;
type PodcastSort = (typeof PODCAST_SORTS)[number];

function normalizeSort(raw: string | undefined): PodcastSort {
    return (PODCAST_SORTS as readonly string[]).includes(raw ?? "")
        ? (raw as PodcastSort)
        : "show_count_desc";
}

function orderByFor(
    sort: PodcastSort,
): Prisma.PodcastOrderByWithRelationInput[] {
    switch (sort) {
        case "show_count_desc":
        case "popularity_desc":
            return [
                { episodes: { _count: "desc" } },
                { title: "asc" },
                { id: "asc" },
            ];
        case "show_count_asc":
        case "popularity_asc":
            return [
                { episodes: { _count: "asc" } },
                { title: "asc" },
                { id: "asc" },
            ];
        case "name_asc":
            return [{ title: "asc" }, { id: "asc" }];
        case "name_desc":
            return [{ title: "desc" }, { id: "asc" }];
        case "activity_desc":
            return [{ updatedAt: "desc" }, { id: "desc" }];
        case "activity_asc":
            return [{ updatedAt: "asc" }, { id: "asc" }];
        case "inserted_at_desc":
            return [{ createdAt: "desc" }, { id: "desc" }];
        case "inserted_at_asc":
            return [{ createdAt: "asc" }, { id: "asc" }];
    }
}

export async function getSearchedPodcasts(params: {
    q?: string;
    page?: string;
    size?: string;
    sort?: string;
    includeEmpty?: string;
    profileId?: string;
}): Promise<PodcastSearchResponse> {
    const query = params.q?.trim() ?? "";
    const page = normalizePage(params.page);
    const size = normalizeSize(params.size);
    const sort = normalizeSort(params.sort);
    const includeEmpty = params.includeEmpty === "true";
    const ownershipWhere = includeEmpty ? {} : PUBLIC_PODCAST_OWNERSHIP_WHERE;
    const queryWhere: Prisma.PodcastWhereInput | null = query
        ? {
              OR: [
                  { title: containsQuery(query) },
                  { authorName: containsQuery(query) },
                  { description: containsQuery(query) },
              ],
          }
        : null;
    const where: Prisma.PodcastWhereInput = queryWhere
        ? { AND: [ownershipWhere, queryWhere] }
        : ownershipWhere;

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
                ...(params.profileId
                    ? {
                          favorites: {
                              where: { profileId: params.profileId },
                              select: { id: true },
                          },
                      }
                    : {}),
            },
            orderBy: orderByFor(sort),
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
            imageUrl: buildPodcastArtworkUrl(podcast.imageUrl),
            description: plainText(podcast.description),
            episodeCount: podcast._count.episodes,
            isFavorite: Boolean(
                (podcast as typeof podcast & { favorites?: { id: number }[] })
                    .favorites?.length,
            ),
        })),
        // Podcasts have no tag-driven filters yet, but the shared FilterBar /
        // FilterModal contract requires a filters array — keep it empty until a
        // podcast tag taxonomy exists.
        filters: [],
    };
}
