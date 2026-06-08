import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { db } from "@/lib/db";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { Prisma } from "@prisma/client";
import { NotFoundError } from "@/objects/NotFoundError";
import { PodcastAppearanceDTO } from "@/objects/class/comedian/podcastAppearance.interface";
import { normalizePodcastAppearanceRole } from "@/lib/data/podcast/appearanceRole";

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

const APPEARANCE_ROLE_PRIORITY: Record<string, number> = {
    host: 3,
    cohost: 2,
    guest: 1,
};

// The scraper occasionally writes the same logical podcast episode to multiple
// `podcast_episodes` rows — different RSS feeds re-publishing the same content,
// or one feed adding a numeric prefix to a title that another feed omits. Each
// row gets its own `episode_appearances` join, so a comedian's appearances list
// returns the same episode 2-4× in a row from the iOS Podcasts tab's perspective.
// Investigation (2026-06-08): 29,314 dupe groups in podcast_episodes affecting
// 29,435 surplus rows. The appearance table itself is unique on
// (episode_id, comedian_id) — the duplication is upstream.
//
// Dedup key: (podcastId, releaseDate.getTime()) when releaseDate is present.
// Same podcast emitting two episodes at the same second is implausible —
// observed dupes always share the timestamp because they come from the same
// upstream feed entry rescraped under different prefix variants. Falls back to
// (podcastId, title) when releaseDate is null so legacy rows still dedupe.
//
// Tiebreaker: prefer host > cohost > guest, then higher `appearance.id` so the
// most-recently-scraped row wins (likely to carry the freshest audio_url).
export function dedupePodcastAppearances(
    appearances: AcceptedEpisodeAppearance[],
): AcceptedEpisodeAppearance[] {
    const byKey = new Map<string, AcceptedEpisodeAppearance>();
    for (const appearance of appearances) {
        const podcastId = appearance.episode.podcast.id;
        const releaseStamp = appearance.episode.releaseDate?.getTime();
        const key =
            releaseStamp !== undefined
                ? `${podcastId}|t:${releaseStamp}`
                : `${podcastId}|n:${appearance.episode.title}`;

        const existing = byKey.get(key);
        if (!existing) {
            byKey.set(key, appearance);
            continue;
        }

        const existingPriority =
            APPEARANCE_ROLE_PRIORITY[
                normalizePodcastAppearanceRole(existing.appearanceRole)
            ] ?? 0;
        const candidatePriority =
            APPEARANCE_ROLE_PRIORITY[
                normalizePodcastAppearanceRole(appearance.appearanceRole)
            ] ?? 0;
        if (
            candidatePriority > existingPriority ||
            (candidatePriority === existingPriority &&
                appearance.id > existing.id)
        ) {
            byKey.set(key, appearance);
        }
    }
    return Array.from(byKey.values());
}

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
            showCount: comedianData.lineupItems.length,
            dates: comedianData.lineupItems.map((item) => ({
                id: item.show.id,
                date: item.show.date,
                name: item.show.name,
                clubId: item.show.club.id,
                clubName: item.show.club.name,
                clubCity: item.show.club.city,
                clubState: item.show.club.state,
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
