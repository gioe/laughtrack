import { db } from "@/lib/db";
import { NotFoundError } from "@/objects/NotFoundError";
import type { PodcastDetailResponse, PodcastEpisodeDTO } from "../interface";
import type { SocialDataDTO } from "@/objects/class/socialData/socialData.interface";
import { buildPodcastArtworkUrl } from "@/lib/data/podcast/imageUrl";
import {
    ACCEPTED_PODCAST_COHOST_WHERE,
    ACCEPTED_PODCAST_HOST_WHERE,
    PUBLIC_PODCAST_ACCEPTED_ATTRIBUTION_WHERE,
} from "@/lib/data/podcast/publicWhere";

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
    profileId?: string,
): Promise<PodcastDetailResponse> {
    const podcast = await db.podcast.findFirst({
        where: {
            ...where,
            ...PUBLIC_PODCAST_ACCEPTED_ATTRIBUTION_WHERE,
        },
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
            comedianPodcasts: {
                where: {
                    OR: [
                        ACCEPTED_PODCAST_HOST_WHERE,
                        ACCEPTED_PODCAST_COHOST_WHERE,
                    ],
                },
                select: {
                    associationType: true,
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
                orderBy: [{ associationType: "desc" }, { comedianId: "asc" }],
            },
            _count: {
                select: {
                    episodes: true,
                },
            },
            ...(profileId
                ? {
                      favorites: {
                          where: { profileId },
                          select: { id: true },
                      },
                  }
                : {}),
        },
    });

    if (!podcast) {
        throw new NotFoundError("Podcast not found");
    }

    const hostLinks = podcast.comedianPodcasts.filter(
        (link) => link.associationType === "host",
    );
    const attributedLinks =
        hostLinks.length > 0
            ? hostLinks
            : podcast.comedianPodcasts.filter(
                  (link) => link.associationType === "cohost",
              );
    const comedianById = new Map(
        attributedLinks.map((link) => [link.comedian.id, link.comedian]),
    );

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
            imageUrl: buildPodcastArtworkUrl(podcast.imageUrl),
            description: plainText(podcast.description),
            episodeCount: podcast._count.episodes,
            isFavorite: Boolean(
                (podcast as typeof podcast & { favorites?: { id: number }[] })
                    .favorites?.length,
            ),
        },
        episodes: podcast.episodes.map(mapEpisode),
        relatedComedians,
    };
}

export async function getPodcastDetailPageData(
    slug: string,
    profileId?: string,
): Promise<PodcastDetailResponse> {
    return getPodcastDetailPageDataByWhere({ slug }, profileId);
}

export async function getPodcastDetailPageDataById(
    id: number,
    profileId?: string,
): Promise<PodcastDetailResponse> {
    return getPodcastDetailPageDataByWhere({ id }, profileId);
}
