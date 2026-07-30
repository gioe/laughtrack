import { db } from "@/lib/db";
import { NotFoundError } from "@/objects/NotFoundError";
import type {
    PodcastEpisodeDetailResponse,
    PodcastHostDTO,
} from "../interface";
import { buildPodcastArtworkUrl } from "@/lib/data/podcast/imageUrl";
import {
    ACCEPTED_PODCAST_COHOST_WHERE,
    ACCEPTED_PODCAST_HOST_WHERE,
    getPublicPodcastAcceptedAttributionWhere,
} from "@/lib/data/podcast/publicWhere";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { mapEpisode, plainText } from "./getPodcastDetailPageData";

export async function getPodcastEpisodeDetailPageData(
    id: number,
): Promise<PodcastEpisodeDetailResponse> {
    const publicPodcastWhere = await getPublicPodcastAcceptedAttributionWhere();
    const episode = await db.podcastEpisode.findFirst({
        where: {
            id,
            podcast: {
                is: publicPodcastWhere,
            },
        },
        select: {
            id: true,
            title: true,
            description: true,
            releaseDate: true,
            durationSeconds: true,
            episodeUrl: true,
            audioUrl: true,
            appearances: {
                where: {
                    reviewStatus: "accepted",
                    comedian: { visible: true },
                },
                select: {
                    comedian: {
                        select: {
                            id: true,
                            uuid: true,
                            name: true,
                            hasImage: true,
                        },
                    },
                },
            },
            podcast: {
                select: {
                    id: true,
                    slug: true,
                    title: true,
                    authorName: true,
                    websiteUrl: true,
                    feedUrl: true,
                    imageUrl: true,
                    description: true,
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
                                },
                            },
                        },
                        orderBy: [
                            { associationType: "desc" },
                            { comedianId: "asc" },
                        ],
                    },
                    _count: {
                        select: {
                            episodes: true,
                        },
                    },
                },
            },
        },
    });

    if (!episode) {
        throw new NotFoundError("Podcast episode not found");
    }

    const hostLinks = episode.podcast.comedianPodcasts.filter(
        (link) => link.associationType === "host",
    );
    const attributedLinks =
        hostLinks.length > 0
            ? hostLinks
            : episode.podcast.comedianPodcasts.filter(
                  (link) => link.associationType === "cohost",
              );
    const hosts: PodcastHostDTO[] = attributedLinks
        .map((link) => link.comedian)
        .sort((a, b) => a.name.localeCompare(b.name))
        .map((comedian) => ({
            id: comedian.id,
            uuid: comedian.uuid,
            name: comedian.name,
            imageUrl: buildComedianImageUrl(
                comedian.name,
                Boolean(comedian.hasImage),
            ),
        }));

    return {
        podcast: {
            id: episode.podcast.id,
            slug: episode.podcast.slug,
            title: episode.podcast.title,
            authorName: episode.podcast.authorName,
            websiteUrl: episode.podcast.websiteUrl,
            feedUrl: episode.podcast.feedUrl,
            imageUrl: buildPodcastArtworkUrl(episode.podcast.imageUrl),
            description: plainText(episode.podcast.description),
            episodeCount: episode.podcast._count.episodes,
            hosts,
        },
        episode: mapEpisode(episode),
    };
}
