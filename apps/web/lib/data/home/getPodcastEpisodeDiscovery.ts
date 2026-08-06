import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import { buildComedianImageUrls } from "@/lib/data/comedian/imageAssets";
import { buildPodcastArtworkUrl } from "@/lib/data/podcast/imageUrl";
import {
    normalizePodcastAppearanceRole,
    type PodcastAppearanceRoleBucket,
} from "@/lib/data/podcast/appearanceRole";
import { stripHtmlTags } from "@/util/primatives/stringUtil";

const DEFAULT_LIMIT = 8;
const MAX_LIMIT = 50;
const RECENCY_DAYS = 30;
const MIN_CANDIDATE_POOL = 200;
const CANDIDATE_POOL_MULTIPLIER = 25;
const MAX_CANDIDATE_POOL = 1_000;
const MAX_PER_PODCAST = 2;
const MAX_PER_COMEDIAN = 2;

export type PodcastEpisodeRecommendationReason =
    | "followed_comedian"
    | "favorite_podcast"
    | "guest_appearance"
    | "popular_comedian"
    | "recent_episode";

export interface PodcastEpisodeDiscoveryDTO {
    id: number;
    title: string;
    description: string | null;
    releaseDate: Date;
    durationSeconds: number | null;
    episodeUrl: string | null;
    audioUrl: string | null;
    podcast: {
        id: number;
        slug: string;
        title: string;
        imageUrl: string | null;
    };
    recommendation: {
        reason: PodcastEpisodeRecommendationReason;
        comedian: {
            id: number;
            uuid: string;
            name: string;
            imageUrl: string;
        };
        appearanceRole: PodcastAppearanceRoleBucket;
        followedComedian: boolean;
        favoritePodcast: boolean;
    };
}

export interface PodcastEpisodeDiscoveryCandidate {
    appearanceId: number;
    appearanceRole: string;
    episodeId: number;
    episodeGuid: string | null;
    episodeTitle: string;
    episodeDescription: string | null;
    releaseDate: Date;
    durationSeconds: number | null;
    episodeUrl: string | null;
    audioUrl: string | null;
    podcastId: number;
    podcastSlug: string;
    podcastTitle: string;
    podcastAuthorName: string | null;
    podcastFeedUrl: string | null;
    podcastImageUrl: string | null;
    comedianId: number;
    comedianUuid: string;
    comedianName: string;
    comedianPopularity: number;
    comedianHasImage: boolean;
    comedianAvatarPath: string | null;
    followedComedian: boolean;
    favoritePodcast: boolean;
}

type PodcastEpisodeDiscoveryRow = {
    appearance_id: number;
    appearance_role: string;
    episode_id: number;
    episode_guid: string | null;
    episode_title: string;
    episode_description: string | null;
    release_date: Date;
    duration_seconds: number | null;
    episode_url: string | null;
    audio_url: string | null;
    podcast_id: number;
    podcast_slug: string;
    podcast_title: string;
    podcast_author_name: string | null;
    podcast_feed_url: string | null;
    podcast_image_url: string | null;
    comedian_id: number;
    comedian_uuid: string;
    comedian_name: string;
    comedian_popularity: number;
    comedian_has_image: boolean;
    comedian_avatar_path: string | null;
    followed_comedian: boolean;
    favorite_podcast: boolean;
};

type PodcastEpisodeDiscoveryQueryArgs = {
    profileId: string | null;
    now: Date;
    cutoff: Date;
    candidateLimit: number;
};

export function buildPodcastEpisodeDiscoveryQuery({
    profileId,
    now,
    cutoff,
    candidateLimit,
}: PodcastEpisodeDiscoveryQueryArgs): Prisma.Sql {
    const followedComedian = profileId
        ? Prisma.sql`EXISTS (
              SELECT 1
              FROM favorite_comedians fc
              WHERE fc.profile_id = ${profileId}
                AND fc.comedian_id = c.uuid
          )`
        : Prisma.sql`FALSE`;
    const favoritePodcast = profileId
        ? Prisma.sql`EXISTS (
              SELECT 1
              FROM favorite_podcasts fp
              WHERE fp.profile_id = ${profileId}
                AND fp.podcast_id = p.id
          )`
        : Prisma.sql`FALSE`;

    return Prisma.sql`
        SELECT
            ea.id AS appearance_id,
            ea.appearance_role,
            pe.id AS episode_id,
            pe.guid AS episode_guid,
            pe.title AS episode_title,
            pe.description AS episode_description,
            pe.release_date,
            pe.duration_seconds,
            pe.episode_url,
            pe.audio_url,
            p.id AS podcast_id,
            p.slug AS podcast_slug,
            p.title AS podcast_title,
            p.author_name AS podcast_author_name,
            p.feed_url AS podcast_feed_url,
            p.image_url AS podcast_image_url,
            c.id AS comedian_id,
            c.uuid AS comedian_uuid,
            c.name AS comedian_name,
            c.popularity AS comedian_popularity,
            c.has_image AS comedian_has_image,
            image_asset.avatar_path AS comedian_avatar_path,
            ${followedComedian} AS followed_comedian,
            ${favoritePodcast} AS favorite_podcast
        FROM episode_appearances ea
        JOIN podcast_episodes pe ON pe.id = ea.episode_id
        JOIN podcasts p ON p.id = pe.podcast_id
        JOIN comedians c ON c.id = ea.comedian_id
        LEFT JOIN LATERAL (
            SELECT avatar_path
            FROM comedian_image_assets
            WHERE comedian_id = c.id
              AND is_active = true
              AND avatar_path IS NOT NULL
            ORDER BY published_at DESC, id DESC
            LIMIT 1
        ) image_asset ON true
        WHERE ea.review_status = 'accepted'
          AND pe.release_date >= ${cutoff}
          AND pe.release_date <= ${now}
          AND c.visible = true
          AND c.parent_comedian_id IS NULL
          AND NOT EXISTS (
              SELECT 1
              FROM comedian_deny_list dl
              WHERE lower(btrim(regexp_replace(replace(c.name, chr(160), ' '), '[[:space:]]+', ' ', 'g'))) =
                    lower(btrim(regexp_replace(replace(dl.name, chr(160), ' '), '[[:space:]]+', ' ', 'g')))
          )
          AND NOT EXISTS (
              SELECT 1
              FROM podcast_deny_list pdl
              WHERE pdl.restored_at IS NULL
                AND (
                    pdl.podcast_id = p.id
                    OR (
                        pdl.source = p.source
                        AND pdl.source_podcast_id = p.source_podcast_id
                    )
                    OR (
                        pdl.feed_url IS NOT NULL
                        AND pdl.feed_url = p.feed_url
                    )
                )
          )
        ORDER BY
            followed_comedian DESC,
            favorite_podcast DESC,
            CASE
                WHEN lower(regexp_replace(btrim(ea.appearance_role), '[-_[:space:]]+', '_', 'g')) = 'guest'
                    THEN 1
                ELSE 0
            END DESC,
            c.popularity DESC,
            pe.release_date DESC,
            p.id ASC,
            pe.id ASC,
            c.id ASC,
            ea.id ASC
        LIMIT ${candidateLimit}
    `;
}

function normalizedValue(value: string): string {
    return value.trim().toLocaleLowerCase("en-US");
}

function normalizedUrl(value: string): string {
    return normalizedValue(value).replace(/\/+$/, "");
}

function normalizedEpisodeTitle(value: string): string {
    return normalizedValue(
        value.replace(
            /^\s*(?:(?:ep(?:isode)?|#)\s*\d+(?:\s*[:.\-)\]]|\s+)\s*|\d+\s*[:.\-)\]]\s*)/i,
            "",
        ),
    ).replace(/\s+/g, " ");
}

function logicalPodcastKey(
    candidate: PodcastEpisodeDiscoveryCandidate,
): string {
    if (candidate.podcastFeedUrl?.trim()) {
        return `feed:${normalizedUrl(candidate.podcastFeedUrl)}`;
    }
    return `catalog:${normalizedValue(candidate.podcastTitle)}|${normalizedValue(candidate.podcastAuthorName ?? "")}`;
}

function logicalEpisodeKeys(
    candidate: PodcastEpisodeDiscoveryCandidate,
): string[] {
    const keys: string[] = [];
    if (candidate.episodeGuid?.trim()) {
        keys.push(
            `guid:${logicalPodcastKey(candidate)}|${normalizedValue(candidate.episodeGuid)}`,
        );
    }
    if (candidate.audioUrl?.trim()) {
        keys.push(`audio:${normalizedUrl(candidate.audioUrl)}`);
    }
    return keys.length > 0
        ? keys
        : [
              [
                  "fallback",
                  logicalPodcastKey(candidate),
                  candidate.releaseDate.getTime(),
                  normalizedEpisodeTitle(candidate.episodeTitle),
              ].join("|"),
          ];
}

function compareCandidates(
    left: PodcastEpisodeDiscoveryCandidate,
    right: PodcastEpisodeDiscoveryCandidate,
): number {
    return (
        Number(right.followedComedian) - Number(left.followedComedian) ||
        Number(right.favoritePodcast) - Number(left.favoritePodcast) ||
        Number(
            normalizePodcastAppearanceRole(right.appearanceRole) === "guest",
        ) -
            Number(
                normalizePodcastAppearanceRole(left.appearanceRole) ===
                    "guest",
            ) ||
        right.comedianPopularity - left.comedianPopularity ||
        right.releaseDate.getTime() - left.releaseDate.getTime() ||
        left.podcastId - right.podcastId ||
        left.episodeId - right.episodeId ||
        left.comedianId - right.comedianId ||
        left.appearanceId - right.appearanceId
    );
}

export function rankPodcastEpisodeDiscoveryCandidates(
    candidates: readonly PodcastEpisodeDiscoveryCandidate[],
    limit = DEFAULT_LIMIT,
): PodcastEpisodeDiscoveryCandidate[] {
    const safeLimit = Math.min(Math.max(0, limit), MAX_LIMIT);
    if (safeLimit === 0) return [];

    const seenEpisodes = new Set<string>();
    const podcastCounts = new Map<string, number>();
    const comedianCounts = new Map<number, number>();
    const selected: PodcastEpisodeDiscoveryCandidate[] = [];

    for (const candidate of [...candidates].sort(compareCandidates)) {
        const episodeKeys = logicalEpisodeKeys(candidate);
        if (episodeKeys.some((key) => seenEpisodes.has(key))) continue;
        for (const key of episodeKeys) seenEpisodes.add(key);

        const podcastKey = logicalPodcastKey(candidate);
        const podcastCount = podcastCounts.get(podcastKey) ?? 0;
        const comedianCount = comedianCounts.get(candidate.comedianId) ?? 0;
        if (
            podcastCount >= MAX_PER_PODCAST ||
            comedianCount >= MAX_PER_COMEDIAN
        ) {
            continue;
        }

        selected.push(candidate);
        podcastCounts.set(podcastKey, podcastCount + 1);
        comedianCounts.set(candidate.comedianId, comedianCount + 1);
        if (selected.length === safeLimit) break;
    }

    return selected;
}

function recommendationReason(
    candidate: PodcastEpisodeDiscoveryCandidate,
): PodcastEpisodeRecommendationReason {
    if (candidate.followedComedian) return "followed_comedian";
    if (candidate.favoritePodcast) return "favorite_podcast";
    if (normalizePodcastAppearanceRole(candidate.appearanceRole) === "guest") {
        return "guest_appearance";
    }
    if (candidate.comedianPopularity > 0) return "popular_comedian";
    return "recent_episode";
}

function mapCandidate(
    candidate: PodcastEpisodeDiscoveryCandidate,
): PodcastEpisodeDiscoveryDTO {
    return {
        id: candidate.episodeId,
        title: candidate.episodeTitle,
        description: candidate.episodeDescription
            ? stripHtmlTags(candidate.episodeDescription) || null
            : null,
        releaseDate: candidate.releaseDate,
        durationSeconds: candidate.durationSeconds,
        episodeUrl: candidate.episodeUrl,
        audioUrl: candidate.audioUrl,
        podcast: {
            id: candidate.podcastId,
            slug: candidate.podcastSlug,
            title: candidate.podcastTitle,
            imageUrl: buildPodcastArtworkUrl(candidate.podcastImageUrl),
        },
        recommendation: {
            reason: recommendationReason(candidate),
            comedian: {
                id: candidate.comedianId,
                uuid: candidate.comedianUuid,
                name: candidate.comedianName,
                imageUrl: buildComedianImageUrls({
                    name: candidate.comedianName,
                    hasImage: candidate.comedianHasImage,
                    activeAsset: candidate.comedianAvatarPath
                        ? { avatarPath: candidate.comedianAvatarPath }
                        : null,
                }).imageUrl,
            },
            appearanceRole: normalizePodcastAppearanceRole(
                candidate.appearanceRole,
            ),
            followedComedian: candidate.followedComedian,
            favoritePodcast: candidate.favoritePodcast,
        },
    };
}

function rowToCandidate(
    row: PodcastEpisodeDiscoveryRow,
): PodcastEpisodeDiscoveryCandidate {
    return {
        appearanceId: row.appearance_id,
        appearanceRole: row.appearance_role,
        episodeId: row.episode_id,
        episodeGuid: row.episode_guid,
        episodeTitle: row.episode_title,
        episodeDescription: row.episode_description,
        releaseDate: row.release_date,
        durationSeconds: row.duration_seconds,
        episodeUrl: row.episode_url,
        audioUrl: row.audio_url,
        podcastId: row.podcast_id,
        podcastSlug: row.podcast_slug,
        podcastTitle: row.podcast_title,
        podcastAuthorName: row.podcast_author_name,
        podcastFeedUrl: row.podcast_feed_url,
        podcastImageUrl: row.podcast_image_url,
        comedianId: row.comedian_id,
        comedianUuid: row.comedian_uuid,
        comedianName: row.comedian_name,
        comedianPopularity: Number(row.comedian_popularity),
        comedianHasImage: row.comedian_has_image,
        comedianAvatarPath: row.comedian_avatar_path,
        followedComedian: row.followed_comedian,
        favoritePodcast: row.favorite_podcast,
    };
}

export async function getPodcastEpisodeDiscovery(
    profileId?: string | null,
    limit = DEFAULT_LIMIT,
): Promise<PodcastEpisodeDiscoveryDTO[]> {
    const safeLimit = Math.min(Math.max(1, limit), MAX_LIMIT);
    const now = new Date();
    const cutoff = new Date(
        now.getTime() - RECENCY_DAYS * 24 * 60 * 60 * 1_000,
    );
    const candidateLimit = Math.min(
        Math.max(safeLimit * CANDIDATE_POOL_MULTIPLIER, MIN_CANDIDATE_POOL),
        MAX_CANDIDATE_POOL,
    );
    const rows = await db.$queryRaw<PodcastEpisodeDiscoveryRow[]>(
        buildPodcastEpisodeDiscoveryQuery({
            profileId: profileId ?? null,
            now,
            cutoff,
            candidateLimit,
        }),
    );

    return rankPodcastEpisodeDiscoveryCandidates(
        rows.map(rowToCandidate),
        safeLimit,
    ).map(mapCandidate);
}
