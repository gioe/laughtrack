import { db } from "@/lib/db";
import { NotFoundError } from "@/objects/NotFoundError";
import type { PodcastDetailResponse, PodcastEpisodeDTO } from "../interface";
import type { SocialDataDTO } from "@/objects/class/socialData/socialData.interface";

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

function mapEpisode(episode: {
    id: number;
    title: string;
    description: string | null;
    releaseDate: Date | null;
    durationSeconds: number | null;
    episodeUrl: string | null;
    audioUrl: string | null;
}): PodcastEpisodeDTO {
    return {
        id: episode.id,
        title: episode.title,
        description: plainText(episode.description),
        releaseDate: episode.releaseDate,
        durationSeconds: episode.durationSeconds,
        episodeUrl: episode.episodeUrl,
        audioUrl: episode.audioUrl,
    };
}

async function getPodcastDetailPageDataByWhere(
    where: { slug: string } | { id: number },
): Promise<PodcastDetailResponse> {
    const podcast = await db.podcast.findUnique({
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
            episodes: {
                select: {
                    id: true,
                    title: true,
                    description: true,
                    releaseDate: true,
                    durationSeconds: true,
                    episodeUrl: true,
                    audioUrl: true,
                    appearances: {
                        where: { reviewStatus: "accepted" },
                        select: {
                            comedian: {
                                select: {
                                    id: true,
                                    uuid: true,
                                    name: true,
                                    hasImage: true,
                                    bio: true,
                                    linktree: true,
                                    instagramAccount: true,
                                    instagramFollowers: true,
                                    tiktokAccount: true,
                                    tiktokFollowers: true,
                                    youtubeAccount: true,
                                    youtubeFollowers: true,
                                    website: true,
                                    popularity: true,
                                    _count: {
                                        select: {
                                            lineupItems: true,
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
                orderBy: [{ releaseDate: "desc" }, { id: "desc" }],
                take: 50,
            },
            _count: {
                select: {
                    episodes: true,
                },
            },
        },
    });

    if (!podcast) {
        throw new NotFoundError("Podcast not found");
    }

    const comedianById = new Map<
        number,
        (typeof podcast.episodes)[number]["appearances"][number]["comedian"]
    >();
    for (const episode of podcast.episodes) {
        for (const appearance of episode.appearances) {
            comedianById.set(appearance.comedian.id, appearance.comedian);
        }
    }

    const relatedComedians = Array.from(comedianById.values())
        .sort((a, b) => a.name.localeCompare(b.name))
        .map((comedian) => {
            const socialData: SocialDataDTO = {
                id: comedian.id,
                linktree: comedian.linktree,
                instagram_account: comedian.instagramAccount,
                instagram_followers: comedian.instagramFollowers,
                tiktok_account: comedian.tiktokAccount,
                tiktok_followers: comedian.tiktokFollowers,
                youtube_account: comedian.youtubeAccount,
                youtube_followers: comedian.youtubeFollowers,
                website: comedian.website,
                popularity: comedian.popularity,
            };
            return {
                id: comedian.id,
                uuid: comedian.uuid,
                name: comedian.name,
                hasImage: false,
                imageUrl: "",
                social_data: socialData,
                bio: comedian.bio,
                show_count: comedian._count.lineupItems,
            };
        });

    return {
        podcast: {
            id: podcast.id,
            slug: podcast.slug,
            title: podcast.title,
            authorName: podcast.authorName,
            websiteUrl: podcast.websiteUrl,
            feedUrl: podcast.feedUrl,
            imageUrl: safePodcastImageUrl(podcast.imageUrl),
            description: plainText(podcast.description),
            episodeCount: podcast._count.episodes,
        },
        episodes: podcast.episodes.map(mapEpisode),
        relatedComedians,
    };
}

export async function getPodcastDetailPageData(
    slug: string,
): Promise<PodcastDetailResponse> {
    return getPodcastDetailPageDataByWhere({ slug });
}

export async function getPodcastDetailPageDataById(
    id: number,
): Promise<PodcastDetailResponse> {
    return getPodcastDetailPageDataByWhere({ id });
}
