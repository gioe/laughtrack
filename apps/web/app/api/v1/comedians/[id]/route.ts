import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

const HOST_ROLES = new Set(["host", "cohost"]);

type PodcastEpisodeAppearance = {
    id: number;
    appearanceRole: string;
    episode: {
        id: number;
        source: string;
        sourceEpisodeId: string;
        title: string;
        releaseDate: Date | null;
        durationSeconds: number | null;
        episodeUrl: string | null;
        audioUrl: string | null;
        podcast: {
            id: number;
            source: string;
            sourcePodcastId: string;
            title: string;
            imageUrl: string | null;
            websiteUrl: string | null;
            feedUrl: string | null;
            authorName: string | null;
        };
        appearances: {
            id: number;
            appearanceRole: string;
            comedian: {
                id: number;
                uuid: string;
                name: string;
                hasImage: boolean | null;
            };
        }[];
    };
};

function mapPodcastAppearances(appearances: PodcastEpisodeAppearance[]) {
    return appearances.map((appearance) => {
        const lineup = appearance.episode.appearances.map((lineupItem) => ({
            id: lineupItem.comedian.id,
            uuid: lineupItem.comedian.uuid,
            name: lineupItem.comedian.name,
            imageUrl: buildComedianImageUrl(
                lineupItem.comedian.name,
                Boolean(lineupItem.comedian.hasImage),
            ),
            hasImage: Boolean(lineupItem.comedian.hasImage),
            role: lineupItem.appearanceRole,
        }));

        return {
            id: appearance.id,
            role: appearance.appearanceRole,
            podcast: {
                id: appearance.episode.podcast.id,
                source: appearance.episode.podcast.source,
                sourcePodcastId: appearance.episode.podcast.sourcePodcastId,
                title: appearance.episode.podcast.title,
                imageUrl: appearance.episode.podcast.imageUrl,
                websiteUrl: appearance.episode.podcast.websiteUrl,
                feedUrl: appearance.episode.podcast.feedUrl,
                authorName: appearance.episode.podcast.authorName,
            },
            episode: {
                id: appearance.episode.id,
                source: appearance.episode.source,
                sourceEpisodeId: appearance.episode.sourceEpisodeId,
                title: appearance.episode.title,
                audioUrl: appearance.episode.audioUrl ?? "",
                episodeUrl:
                    appearance.episode.episodeUrl ??
                    appearance.episode.audioUrl,
                releaseDate:
                    appearance.episode.releaseDate?.toISOString() ?? null,
                durationSeconds: appearance.episode.durationSeconds,
                hosts: lineup.filter((lineupItem) =>
                    HOST_ROLES.has(lineupItem.role),
                ),
                guests: lineup.filter(
                    (lineupItem) => !HOST_ROLES.has(lineupItem.role),
                ),
            },
        };
    });
}

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> },
) {
    const rl = await applyPublicReadRateLimit(req, "comedians-id");
    if (rl instanceof NextResponse) return rl;

    const { id } = await params;
    const numericId = Number(id);

    if (!Number.isInteger(numericId)) {
        return NextResponse.json(
            { error: "Invalid id" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    try {
        const comedian = await db.comedian.findUnique({
            where: { id: numericId },
            select: {
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
                episodeAppearances: {
                    select: {
                        id: true,
                        appearanceRole: true,
                        episode: {
                            select: {
                                id: true,
                                source: true,
                                sourceEpisodeId: true,
                                title: true,
                                releaseDate: true,
                                durationSeconds: true,
                                episodeUrl: true,
                                audioUrl: true,
                                podcast: {
                                    select: {
                                        id: true,
                                        source: true,
                                        sourcePodcastId: true,
                                        title: true,
                                        imageUrl: true,
                                        websiteUrl: true,
                                        feedUrl: true,
                                        authorName: true,
                                    },
                                },
                                appearances: {
                                    select: {
                                        id: true,
                                        appearanceRole: true,
                                        comedian: {
                                            select: {
                                                id: true,
                                                uuid: true,
                                                name: true,
                                                hasImage: true,
                                            },
                                        },
                                    },
                                    where: {
                                        reviewStatus: "accepted",
                                    },
                                    orderBy: [
                                        { appearanceRole: "asc" },
                                        { id: "asc" },
                                    ],
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
                    orderBy: [
                        { episode: { releaseDate: "desc" } },
                        { id: "desc" },
                    ],
                },
            },
        });

        if (!comedian) {
            return NextResponse.json(
                { error: "Comedian not found" },
                { status: 404, headers: rateLimitHeaders(rl) },
            );
        }

        return NextResponse.json(
            {
                data: {
                    id: comedian.id,
                    uuid: comedian.uuid,
                    name: comedian.name,
                    imageUrl: buildComedianImageUrl(
                        comedian.name,
                        comedian.hasImage,
                    ),
                    hasImage: Boolean(comedian.hasImage),
                    social_data: {
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
                    },
                    podcastAppearances: mapPodcastAppearances(
                        comedian.episodeAppearances,
                    ),
                },
            },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/comedians/[id] error:", error);
        return NextResponse.json(
            { error: "Failed to fetch comedian" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
