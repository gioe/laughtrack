import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { db } from "@/lib/db";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { Prisma } from "@prisma/client";
import { NotFoundError } from "@/objects/NotFoundError";
import { ComedianPodcastAppearanceDTO } from "@/objects/class/comedian/podcastAppearance.interface";

function buildComedianSelect() {
    return {
        id: true,
        uuid: true,
        name: true,
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
        hasImage: true,
        lineupItems: {
            select: {
                id: true,
                show: {
                    select: {
                        id: true,
                        date: true,
                        name: true,
                        club: {
                            select: {
                                id: true,
                                name: true,
                                city: true,
                                state: true,
                            },
                        },
                    },
                },
            },
            where: {
                show: {
                    date: {
                        gt: new Date(),
                    },
                },
            },
        },
        episodeAppearances: {
            select: {
                id: true,
                appearanceRole: true,
                episode: {
                    select: {
                        title: true,
                        releaseDate: true,
                        episodeUrl: true,
                        audioUrl: true,
                        durationSeconds: true,
                        podcast: {
                            select: {
                                title: true,
                            },
                        },
                    },
                },
            },
            where: {
                reviewStatus: "accepted",
                AND: [
                    {
                        episode: {
                            audioUrl: {
                                not: null,
                            },
                        },
                    },
                    {
                        episode: {
                            audioUrl: {
                                not: "",
                            },
                        },
                    },
                ],
            },
            orderBy: [{ episode: { releaseDate: "desc" } }, { id: "desc" }],
        },
    } satisfies Prisma.ComedianSelect;
}

function sortPodcastAppearances(
    appearances: ComedianPodcastAppearanceDTO[],
): ComedianPodcastAppearanceDTO[] {
    return [...appearances].sort((a, b) => {
        if (!a.releaseDate && !b.releaseDate) {
            return b.id - a.id;
        }
        if (!a.releaseDate) return 1;
        if (!b.releaseDate) return -1;

        return (
            new Date(b.releaseDate).getTime() -
            new Date(a.releaseDate).getTime()
        );
    });
}

type AcceptedEpisodeAppearance = {
    id: number;
    appearanceRole: string;
    episode: {
        title: string;
        releaseDate: Date | null;
        episodeUrl: string | null;
        audioUrl: string | null;
        durationSeconds: number | null;
        podcast: {
            title: string;
        };
    };
};

function mapEpisodeAppearances(
    appearances: AcceptedEpisodeAppearance[],
): ComedianPodcastAppearanceDTO[] {
    return appearances.map((appearance) => ({
        id: appearance.id,
        podcastName: appearance.episode.podcast.title,
        episodeTitle: appearance.episode.title,
        releaseDate: appearance.episode.releaseDate,
        episodeUrl: appearance.episode.episodeUrl ?? "",
        audioUrl: appearance.episode.audioUrl,
        durationSeconds: appearance.episode.durationSeconds,
        appearanceRole: appearance.appearanceRole,
    }));
}

export async function findComedianByName(
    helper: QueryHelper,
): Promise<ComedianDTO> {
    try {
        const name = helper.getSlug();
        if (!name) {
            throw new Error("Comedian name is required");
        }

        const comedianData = await db.comedian.findFirst({
            where: {
                name: {
                    equals: name,
                    mode: Prisma.QueryMode.insensitive,
                },
            },
            select: {
                ...buildComedianSelect(),
                ...(helper.getProfileId()
                    ? {
                          favoriteComedians: {
                              where: {
                                  profileId: helper.getProfileId(),
                              },
                              select: {
                                  id: true,
                              },
                          },
                      }
                    : {}),
            },
        });

        if (!comedianData) {
            throw new NotFoundError(`Comedian with name "${name}" not found`);
        }

        return {
            name: comedianData.name,
            id: comedianData.id,
            imageUrl: buildComedianImageUrl(
                comedianData.name,
                comedianData.hasImage,
            ),
            hasImage: Boolean(comedianData.hasImage),
            uuid: comedianData.uuid,
            isFavorite: Boolean(comedianData.favoriteComedians?.length),
            show_count: comedianData.lineupItems.length,
            dates: comedianData.lineupItems.map((item) => ({
                id: item.show.id,
                date: item.show.date,
                name: item.show.name,
                clubID: item.show.club.id,
                clubName: item.show.club.name,
                clubCity: item.show.club.city,
                clubState: item.show.club.state,
                imageUrl: buildComedianImageUrl(
                    comedianData.name,
                    comedianData.hasImage,
                ),
            })),
            bio: comedianData.bio,
            social_data: {
                id: comedianData.id,
                linktree: comedianData.linktree,
                instagram_account: comedianData.instagramAccount,
                instagram_followers: comedianData.instagramFollowers,
                tiktok_account: comedianData.tiktokAccount,
                tiktok_followers: comedianData.tiktokFollowers,
                youtube_account: comedianData.youtubeAccount,
                youtube_followers: comedianData.youtubeFollowers,
                website: comedianData.website,
                popularity: comedianData.popularity,
            },
            podcastAppearances: sortPodcastAppearances(
                mapEpisodeAppearances(comedianData.episodeAppearances),
            ),
        };
    } catch (error) {
        if (error instanceof Error) {
            console.error("Error in findComedianByName:", error);
            throw error;
        }
        throw new Error(
            "An unknown error occurred while fetching comedian details",
        );
    }
}
