import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { db } from "@/lib/db";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { Prisma } from "@prisma/client";
import { NotFoundError } from "@/objects/NotFoundError";
import { PodcastAppearanceDTO } from "@/objects/class/comedian/podcastAppearance.interface";
import { normalizePodcastAppearanceRole } from "@/lib/data/podcast/appearanceRole";
import { dedupePodcastAppearances } from "@/lib/data/podcast/dedupePodcastAppearances";
import { resolveCanonicalComedianIdentityById } from "./resolveCanonicalComedianIdentity";
import { AVAILABLE_SHOW_WHERE } from "@/lib/data/show/showSelect";
import { computeShowSoldOut } from "@/util/show/soldOutUtil";

function buildComedianSelect() {
    return {
        id: true,
        uuid: true,
        name: true,
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
        homeCity: true,
        homeState: true,
        homeCountry: true,
        homeClub: {
            select: {
                id: true,
                name: true,
            },
        },
        episodeAppearances: {
            select: {
                id: true,
                appearanceRole: true,
                episode: {
                    select: {
                        // Selected so dedupePodcastAppearances can collapse
                        // duplicate podcast_episodes rows for one logical episode.
                        // Not surfaced on PodcastAppearanceDTO.
                        id: true,
                        title: true,
                        releaseDate: true,
                        episodeUrl: true,
                        audioUrl: true,
                        durationSeconds: true,
                        podcast: {
                            select: {
                                id: true,
                                title: true,
                                imageUrl: true,
                                authorName: true,
                                websiteUrl: true,
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
    appearances: PodcastAppearanceDTO[],
): PodcastAppearanceDTO[] {
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
        id: number;
        title: string;
        releaseDate: Date | null;
        episodeUrl: string | null;
        audioUrl: string | null;
        durationSeconds: number | null;
        podcast: {
            id: number;
            title: string;
            imageUrl: string | null;
            authorName: string | null;
            websiteUrl: string | null;
        };
    };
};

function mapEpisodeAppearances(
    appearances: AcceptedEpisodeAppearance[],
): PodcastAppearanceDTO[] {
    return appearances.map((appearance) => ({
        id: appearance.id,
        podcastName: appearance.episode.podcast.title,
        podcastImageUrl: appearance.episode.podcast.imageUrl,
        podcastAuthorName: appearance.episode.podcast.authorName,
        podcastWebsiteUrl: appearance.episode.podcast.websiteUrl,
        episodeTitle: appearance.episode.title,
        releaseDate: appearance.episode.releaseDate,
        episodeUrl: appearance.episode.episodeUrl ?? "",
        audioUrl: appearance.episode.audioUrl,
        durationSeconds: appearance.episode.durationSeconds,
        appearanceRole: normalizePodcastAppearanceRole(
            appearance.appearanceRole,
        ),
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
                visible: true,
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

        const identity = await resolveCanonicalComedianIdentityById(
            comedianData.id,
        );
        const canonicalUpcomingShows = identity
            ? await db.show.findMany({
                  where: {
                      date: { gte: new Date() },
                      club: { visible: true },
                      lineupItems: {
                          some: {
                              comedianId: { in: identity.memberUuids },
                          },
                      },
                      AND: [AVAILABLE_SHOW_WHERE],
                  },
                  select: {
                      id: true,
                      date: true,
                      name: true,
                      tickets: { select: { soldOut: true } },
                      club: {
                          select: {
                              id: true,
                              name: true,
                              city: true,
                              state: true,
                          },
                      },
                  },
                  orderBy: [{ date: "asc" }, { id: "asc" }],
              })
            : [];
        const availableUpcomingShows = canonicalUpcomingShows.filter(
            (show) => !computeShowSoldOut(show.name, show.tickets),
        );

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
            showCount: availableUpcomingShows.length,
            dates: availableUpcomingShows.map((show) => ({
                id: show.id,
                date: show.date,
                name: show.name,
                clubId: show.club.id,
                clubName: show.club.name,
                clubCity: show.club.city,
                clubState: show.club.state,
                imageUrl: buildComedianImageUrl(
                    comedianData.name,
                    comedianData.hasImage,
                ),
            })),
            socialData: {
                id: comedianData.id,
                linktree: comedianData.linktree,
                instagramAccount: comedianData.instagramAccount,
                instagramFollowers: comedianData.instagramFollowers,
                tiktokAccount: comedianData.tiktokAccount,
                tiktokFollowers: comedianData.tiktokFollowers,
                youtubeAccount: comedianData.youtubeAccount,
                youtubeFollowers: comedianData.youtubeFollowers,
                website: comedianData.website,
                popularity: comedianData.popularity,
            },
            podcastAppearances: sortPodcastAppearances(
                mapEpisodeAppearances(
                    dedupePodcastAppearances(comedianData.episodeAppearances),
                ),
            ),
            homeLocation: {
                city: comedianData.homeCity,
                state: comedianData.homeState,
                country: comedianData.homeCountry,
                club: comedianData.homeClub
                    ? {
                          id: comedianData.homeClub.id,
                          name: comedianData.homeClub.name,
                      }
                    : null,
            },
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
