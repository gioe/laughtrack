import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import {
    normalizePodcastAppearanceRole,
    type PodcastAppearanceRoleBucket,
} from "@/lib/data/podcast/appearanceRole";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { findShowsForHome } from "./findShowsForHome";

const DAY_MS = 24 * 60 * 60 * 1_000;
const DEFAULT_HORIZON_DAYS = 90;
const DEFAULT_LIMIT = 8;
const MAX_LIMIT = 50;
const RECENT_PODCAST_APPEARANCE_DAYS = 30;

export type PodcastAffinityAttribution =
    | "host"
    | "cohost"
    | "recent_appearance";

export interface AffinityPerformer {
    id: number;
    uuid: string;
    name: string;
}

export interface AffinityPodcast {
    id: number;
    slug: string;
    title: string;
}

export interface FromYourPodcastsReason {
    kind: "from_your_podcasts";
    label: string;
    evidence: {
        canonicalComedianId: number;
        podcast: AffinityPodcast;
        attribution: PodcastAffinityAttribution;
        appearanceRole: PodcastAppearanceRoleBucket | null;
        episode: {
            id: number;
            title: string;
            releaseDate: Date;
        } | null;
    };
}

export interface BecauseYouFollowThemReason {
    kind: "because_you_follow_them";
    label: string;
    evidence: {
        canonicalComedianId: number;
    };
}

export interface FromYourPodcastsRailItem {
    show: ShowDTO;
    performer: AffinityPerformer;
    podcast: AffinityPodcast;
    reason: FromYourPodcastsReason;
}

export interface BecauseYouFollowThemRailItem {
    show: ShowDTO;
    performer: AffinityPerformer;
    reason: BecauseYouFollowThemReason;
}

export interface AffinityRails {
    fromYourPodcasts: {
        railKey: "from_your_podcasts";
        label: "From your podcasts";
        items: FromYourPodcastsRailItem[];
    };
    becauseYouFollowThem: {
        railKey: "because_you_follow_them";
        label: "Because you follow them";
        items: BecauseYouFollowThemRailItem[];
    };
}

export interface AffinityRailsOptions {
    now?: Date;
    horizonDays?: number;
    limit?: number;
    excludedShowIds?: readonly number[];
    /**
     * Keep the provider's historical fixed rail priority by default. The home
     * feed disables this so its operator-configured policy can own cross-rail
     * deduplication after rotation has been resolved.
     */
    deduplicateAcrossRails?: boolean;
}

export interface AffinityEvidenceRow {
    showId: number;
    showDate: Date;
    showName: string | null;
    clubVisible: boolean;
    performerVisible: boolean;
    canonicalVisible: boolean;
    ticketsSoldOut: boolean;
    hasPurchasePath: boolean;
    canonicalComedianId: number;
    canonicalComedianUuid: string;
    canonicalComedianName: string;
    favoriteComedian: boolean;
    podcastId: number | null;
    podcastSlug: string | null;
    podcastTitle: string | null;
    podcastAttribution: string | null;
    appearanceRole: string | null;
    episodeId: number | null;
    episodeTitle: string | null;
    episodeReleaseDate: Date | null;
}

interface ClassifyOptions {
    now: Date;
    horizonDays: number;
    limit: number;
    personalized: boolean;
    excludedShowIds: readonly number[];
    deduplicateAcrossRails?: boolean;
}

interface ClassifiedFromPodcastItem {
    showId: number;
    performer: AffinityPerformer;
    podcast: AffinityPodcast;
    reason: FromYourPodcastsReason;
}

interface ClassifiedFollowedItem {
    showId: number;
    performer: AffinityPerformer;
    reason: BecauseYouFollowThemReason;
}

interface ClassifiedAffinityRails {
    fromYourPodcasts: ClassifiedFromPodcastItem[];
    becauseYouFollowThem: ClassifiedFollowedItem[];
}

type AffinityQueryRow = {
    show_id: number;
    show_date: Date;
    show_name: string | null;
    club_visible: boolean;
    performer_visible: boolean;
    canonical_visible: boolean;
    tickets_sold_out: boolean;
    has_purchase_path: boolean;
    canonical_comedian_id: number;
    canonical_comedian_uuid: string;
    canonical_comedian_name: string;
    favorite_comedian: boolean;
    podcast_id: number | null;
    podcast_slug: string | null;
    podcast_title: string | null;
    podcast_attribution: string | null;
    appearance_role: string | null;
    episode_id: number | null;
    episode_title: string | null;
    episode_release_date: Date | null;
};

function comedianNotDenied(alias: string): Prisma.Sql {
    return Prisma.sql`NOT EXISTS (
        SELECT 1
        FROM comedian_deny_list deny
        WHERE lower(btrim(regexp_replace(replace(${Prisma.raw(alias)}.name, chr(160), ' '), '[[:space:]]+', ' ', 'g'))) =
              lower(btrim(regexp_replace(replace(deny.name, chr(160), ' '), '[[:space:]]+', ' ', 'g')))
    )`;
}

export function buildAffinityQuery({
    profileId,
    now,
    horizonEnd,
    appearanceCutoff,
}: {
    profileId: string | null;
    now: Date;
    horizonEnd: Date;
    appearanceCutoff: Date;
}): Prisma.Sql {
    const favoriteComedianProfile = profileId
        ? Prisma.sql`fc.profile_id = ${profileId}`
        : Prisma.sql`FALSE`;
    const favoritePodcastProfile = profileId
        ? Prisma.sql`fp.profile_id = ${profileId}`
        : Prisma.sql`FALSE`;

    return Prisma.sql`
        WITH eligible_shows AS (
            SELECT
                show.id,
                show.date,
                show.name,
                show.tickets_sold_out,
                club.visible AS club_visible
            FROM shows show
            JOIN clubs club ON club.id = show.club_id
            WHERE club.visible = true
              AND show.date > ${now}
              AND show.date <= ${horizonEnd}
              AND show.tickets_sold_out = false
              AND COALESCE(show.name, '') !~* 'sold[ -]?out'
              AND EXISTS (
                  SELECT 1
                  FROM tickets ticket
                  WHERE ticket.show_id = show.id
                    AND ticket.sold_out = false
                    AND NULLIF(btrim(ticket.purchase_url), '') IS NOT NULL
              )
        ),
        canonical_lineup AS (
            SELECT DISTINCT
                show.id AS show_id,
                show.date AS show_date,
                show.name AS show_name,
                show.club_visible,
                show.tickets_sold_out,
                performer.visible AS performer_visible,
                canonical.visible AS canonical_visible,
                canonical.id AS canonical_comedian_id,
                canonical.uuid AS canonical_comedian_uuid,
                canonical.name AS canonical_comedian_name
            FROM eligible_shows show
            JOIN lineup_items lineup ON lineup.show_id = show.id
            JOIN comedians performer ON performer.uuid = lineup.comedian_id
            JOIN comedians canonical
              ON canonical.id = COALESCE(performer.parent_comedian_id, performer.id)
            WHERE performer.visible = true
              AND canonical.visible = true
              AND canonical.parent_comedian_id IS NULL
              AND ${comedianNotDenied("canonical")}
              AND NOT EXISTS (
                  SELECT 1
                  FROM tagged_comedians tagged
                  JOIN tags tag ON tag.id = tagged.tag_id
                  WHERE tagged.comedian_id IN (performer.uuid, canonical.uuid)
                    AND tag."restrictContent" = true
              )
        ),
        favorite_canonical_comedians AS (
            SELECT DISTINCT canonical.id AS canonical_comedian_id
            FROM favorite_comedians fc
            JOIN comedians favorite ON favorite.uuid = fc.comedian_id
            JOIN comedians canonical
              ON canonical.id = COALESCE(favorite.parent_comedian_id, favorite.id)
            WHERE ${favoriteComedianProfile}
              AND favorite.visible = true
              AND canonical.visible = true
              AND canonical.parent_comedian_id IS NULL
              AND ${comedianNotDenied("canonical")}
        ),
        favorite_public_podcasts AS (
            SELECT DISTINCT
                podcast.id,
                podcast.slug,
                podcast.title
            FROM favorite_podcasts fp
            JOIN podcasts podcast ON podcast.id = fp.podcast_id
            WHERE ${favoritePodcastProfile}
              AND NOT EXISTS (
                  SELECT 1
                  FROM podcast_deny_list deny
                  WHERE deny.restored_at IS NULL
                    AND (
                        deny.podcast_id = podcast.id
                        OR (
                            deny.source = podcast.source
                            AND deny.source_podcast_id = podcast.source_podcast_id
                        )
                        OR (
                            deny.feed_url IS NOT NULL
                            AND deny.feed_url = podcast.feed_url
                        )
                    )
              )
        ),
        podcast_affinity_candidates AS (
            SELECT
                canonical.id AS canonical_comedian_id,
                podcast.id AS podcast_id,
                podcast.slug AS podcast_slug,
                podcast.title AS podcast_title,
                CASE
                    WHEN lower(regexp_replace(btrim(link.association_type), '[-_[:space:]]+', '_', 'g')) IN ('cohost', 'co_host')
                        THEN 'cohost'
                    ELSE 'host'
                END AS podcast_attribution,
                NULL::text AS appearance_role,
                NULL::integer AS episode_id,
                NULL::text AS episode_title,
                NULL::timestamptz AS episode_release_date,
                CASE
                    WHEN lower(regexp_replace(btrim(link.association_type), '[-_[:space:]]+', '_', 'g')) = 'host'
                        THEN 0
                    ELSE 1
                END AS attribution_priority
            FROM favorite_public_podcasts podcast
            JOIN comedian_podcasts link ON link.podcast_id = podcast.id
            JOIN comedians attributed ON attributed.id = link.comedian_id
            JOIN comedians canonical
              ON canonical.id = COALESCE(attributed.parent_comedian_id, attributed.id)
            WHERE link.review_status = 'accepted'
              AND lower(regexp_replace(btrim(link.association_type), '[-_[:space:]]+', '_', 'g')) IN ('host', 'cohost', 'co_host')
              AND attributed.visible = true
              AND canonical.visible = true
              AND canonical.parent_comedian_id IS NULL
              AND ${comedianNotDenied("canonical")}

            UNION ALL

            SELECT
                canonical.id AS canonical_comedian_id,
                podcast.id AS podcast_id,
                podcast.slug AS podcast_slug,
                podcast.title AS podcast_title,
                'recent_appearance' AS podcast_attribution,
                appearance.appearance_role,
                episode.id AS episode_id,
                episode.title AS episode_title,
                episode.release_date AS episode_release_date,
                2 AS attribution_priority
            FROM favorite_public_podcasts podcast
            JOIN podcast_episodes episode ON episode.podcast_id = podcast.id
            JOIN episode_appearances appearance ON appearance.episode_id = episode.id
            JOIN comedians attributed ON attributed.id = appearance.comedian_id
            JOIN comedians canonical
              ON canonical.id = COALESCE(attributed.parent_comedian_id, attributed.id)
            WHERE appearance.review_status = 'accepted'
              AND episode.release_date >= ${appearanceCutoff}
              AND episode.release_date <= ${now}
              AND attributed.visible = true
              AND canonical.visible = true
              AND canonical.parent_comedian_id IS NULL
              AND ${comedianNotDenied("canonical")}
        ),
        podcast_affinities AS (
            SELECT DISTINCT ON (candidate.canonical_comedian_id)
                candidate.*
            FROM podcast_affinity_candidates candidate
            ORDER BY
                candidate.canonical_comedian_id,
                candidate.attribution_priority,
                candidate.episode_release_date DESC NULLS LAST,
                candidate.podcast_id,
                candidate.episode_id NULLS LAST
        )
        SELECT
            lineup.show_id,
            lineup.show_date,
            lineup.show_name,
            lineup.club_visible,
            lineup.performer_visible,
            lineup.canonical_visible,
            lineup.tickets_sold_out,
            true AS has_purchase_path,
            lineup.canonical_comedian_id,
            lineup.canonical_comedian_uuid,
            lineup.canonical_comedian_name,
            favorite.canonical_comedian_id IS NOT NULL AS favorite_comedian,
            affinity.podcast_id,
            affinity.podcast_slug,
            affinity.podcast_title,
            affinity.podcast_attribution,
            affinity.appearance_role,
            affinity.episode_id,
            affinity.episode_title,
            affinity.episode_release_date
        FROM canonical_lineup lineup
        LEFT JOIN favorite_canonical_comedians favorite
          ON favorite.canonical_comedian_id = lineup.canonical_comedian_id
        LEFT JOIN podcast_affinities affinity
          ON affinity.canonical_comedian_id = lineup.canonical_comedian_id
        ORDER BY lineup.show_date, lineup.show_id, lineup.canonical_comedian_id
    `;
}

function emptyRails(): AffinityRails {
    return {
        fromYourPodcasts: {
            railKey: "from_your_podcasts",
            label: "From your podcasts",
            items: [],
        },
        becauseYouFollowThem: {
            railKey: "because_you_follow_them",
            label: "Because you follow them",
            items: [],
        },
    };
}

function isEligible(
    row: AffinityEvidenceRow,
    now: Date,
    horizonEnd: Date,
): boolean {
    return (
        row.clubVisible &&
        row.performerVisible &&
        row.canonicalVisible &&
        !row.ticketsSoldOut &&
        !/sold[ -]?out/i.test(row.showName ?? "") &&
        row.hasPurchasePath &&
        row.showDate.getTime() > now.getTime() &&
        row.showDate.getTime() <= horizonEnd.getTime()
    );
}

function attribution(value: string | null): PodcastAffinityAttribution | null {
    if (
        value === "host" ||
        value === "cohost" ||
        value === "recent_appearance"
    ) {
        return value;
    }
    return null;
}

function attributionPriority(value: string | null): number {
    if (value === "host") return 0;
    if (value === "cohost") return 1;
    if (value === "recent_appearance") return 2;
    return 3;
}

function comparePodcastEvidence(
    left: AffinityEvidenceRow,
    right: AffinityEvidenceRow,
): number {
    return (
        attributionPriority(left.podcastAttribution) -
            attributionPriority(right.podcastAttribution) ||
        (right.episodeReleaseDate?.getTime() ?? 0) -
            (left.episodeReleaseDate?.getTime() ?? 0) ||
        (left.podcastId ?? Number.MAX_SAFE_INTEGER) -
            (right.podcastId ?? Number.MAX_SAFE_INTEGER) ||
        left.canonicalComedianId - right.canonicalComedianId
    );
}

function performer(row: AffinityEvidenceRow): AffinityPerformer {
    return {
        id: row.canonicalComedianId,
        uuid: row.canonicalComedianUuid,
        name: row.canonicalComedianName,
    };
}

function podcast(row: AffinityEvidenceRow): AffinityPodcast | null {
    return row.podcastId !== null &&
        row.podcastSlug !== null &&
        row.podcastTitle !== null
        ? {
              id: row.podcastId,
              slug: row.podcastSlug,
              title: row.podcastTitle,
          }
        : null;
}

/**
 * Pure classifier. By default, rail order is also the internal show-dedup
 * priority. Callers with a separate authoritative policy can retain overlaps
 * for that later selector by setting deduplicateAcrossRails=false.
 */
export function classifyAffinityCandidates(
    rows: readonly AffinityEvidenceRow[],
    options: ClassifyOptions,
): ClassifiedAffinityRails {
    const horizonEnd = new Date(
        options.now.getTime() + options.horizonDays * DAY_MS,
    );
    const byShow = new Map<number, AffinityEvidenceRow[]>();
    for (const row of rows) {
        if (!isEligible(row, options.now, horizonEnd)) continue;
        const existing = byShow.get(row.showId) ?? [];
        if (
            !existing.some(
                (candidate) =>
                    candidate.canonicalComedianId === row.canonicalComedianId,
            )
        ) {
            existing.push(row);
            byShow.set(row.showId, existing);
        } else {
            const index = existing.findIndex(
                (candidate) =>
                    candidate.canonicalComedianId === row.canonicalComedianId,
            );
            const prior = existing[index];
            existing[index] = {
                ...(comparePodcastEvidence(row, prior) < 0 ? row : prior),
                favoriteComedian:
                    prior.favoriteComedian || row.favoriteComedian,
            };
        }
    }

    const shows = [...byShow.entries()].sort(
        ([leftId, leftRows], [rightId, rightRows]) =>
            leftRows[0].showDate.getTime() - rightRows[0].showDate.getTime() ||
            leftId - rightId,
    );
    const podcastSeen = new Set(options.excludedShowIds);
    const followedSeen =
        options.deduplicateAcrossRails === false
            ? new Set(options.excludedShowIds)
            : podcastSeen;
    const result: ClassifiedAffinityRails = {
        fromYourPodcasts: [],
        becauseYouFollowThem: [],
    };

    if (options.personalized) {
        for (const [showId, showRows] of shows) {
            if (
                podcastSeen.has(showId) ||
                result.fromYourPodcasts.length >= options.limit
            ) {
                continue;
            }
            const match = [...showRows]
                .filter(
                    (row) =>
                        attribution(row.podcastAttribution) && podcast(row),
                )
                .sort(comparePodcastEvidence)[0];
            const matchAttribution = match
                ? attribution(match.podcastAttribution)
                : null;
            const matchPodcast = match ? podcast(match) : null;
            if (!match || !matchAttribution || !matchPodcast) continue;

            const appearance =
                matchAttribution === "recent_appearance" &&
                match.episodeId !== null &&
                match.episodeTitle !== null &&
                match.episodeReleaseDate !== null
                    ? {
                          id: match.episodeId,
                          title: match.episodeTitle,
                          releaseDate: match.episodeReleaseDate,
                      }
                    : null;
            const label =
                matchAttribution === "host"
                    ? `Featuring ${match.canonicalComedianName}, host of ${matchPodcast.title}`
                    : matchAttribution === "cohost"
                      ? `Featuring ${match.canonicalComedianName}, co-host of ${matchPodcast.title}`
                      : `Featuring ${match.canonicalComedianName} from a recent ${matchPodcast.title} episode`;
            result.fromYourPodcasts.push({
                showId,
                performer: performer(match),
                podcast: matchPodcast,
                reason: {
                    kind: "from_your_podcasts",
                    label,
                    evidence: {
                        canonicalComedianId: match.canonicalComedianId,
                        podcast: matchPodcast,
                        attribution: matchAttribution,
                        appearanceRole:
                            matchAttribution === "recent_appearance"
                                ? normalizePodcastAppearanceRole(
                                      match.appearanceRole,
                                  )
                                : null,
                        episode: appearance,
                    },
                },
            });
            podcastSeen.add(showId);
        }
    }

    if (options.personalized) {
        for (const [showId, showRows] of shows) {
            if (
                followedSeen.has(showId) ||
                result.becauseYouFollowThem.length >= options.limit
            ) {
                continue;
            }
            const match = [...showRows]
                .filter((row) => row.favoriteComedian)
                .sort(
                    (left, right) =>
                        left.canonicalComedianId - right.canonicalComedianId,
                )[0];
            if (!match) continue;
            result.becauseYouFollowThem.push({
                showId,
                performer: performer(match),
                reason: {
                    kind: "because_you_follow_them",
                    label: `Featuring ${match.canonicalComedianName}, whom you follow`,
                    evidence: {
                        canonicalComedianId: match.canonicalComedianId,
                    },
                },
            });
            followedSeen.add(showId);
        }
    }

    return result;
}

function rowToEvidence(row: AffinityQueryRow): AffinityEvidenceRow {
    return {
        showId: row.show_id,
        showDate: row.show_date,
        showName: row.show_name,
        clubVisible: row.club_visible,
        performerVisible: row.performer_visible,
        canonicalVisible: row.canonical_visible,
        ticketsSoldOut: row.tickets_sold_out,
        hasPurchasePath: row.has_purchase_path,
        canonicalComedianId: row.canonical_comedian_id,
        canonicalComedianUuid: row.canonical_comedian_uuid,
        canonicalComedianName: row.canonical_comedian_name,
        favoriteComedian: row.favorite_comedian,
        podcastId: row.podcast_id,
        podcastSlug: row.podcast_slug,
        podcastTitle: row.podcast_title,
        podcastAttribution: row.podcast_attribution,
        appearanceRole: row.appearance_role,
        episodeId: row.episode_id,
        episodeTitle: row.episode_title,
        episodeReleaseDate: row.episode_release_date,
    };
}

export async function getAffinityRails(
    profileId?: string | null,
    options: AffinityRailsOptions = {},
): Promise<AffinityRails> {
    const rails = emptyRails();
    const now = options.now ?? new Date();
    if (Number.isNaN(now.getTime())) return rails;

    const horizonDays = Math.max(
        1,
        Math.min(365, Math.trunc(options.horizonDays ?? DEFAULT_HORIZON_DAYS)),
    );
    const limit = Math.max(
        1,
        Math.min(MAX_LIMIT, Math.trunc(options.limit ?? DEFAULT_LIMIT)),
    );
    const horizonEnd = new Date(now.getTime() + horizonDays * DAY_MS);
    const appearanceCutoff = new Date(
        now.getTime() - RECENT_PODCAST_APPEARANCE_DAYS * DAY_MS,
    );
    const rows = await db.$queryRaw<AffinityQueryRow[]>(
        buildAffinityQuery({
            profileId: profileId ?? null,
            now,
            horizonEnd,
            appearanceCutoff,
        }),
    );
    if (rows.length === 0) return rails;

    const classified = classifyAffinityCandidates(rows.map(rowToEvidence), {
        now,
        horizonDays,
        limit,
        personalized: Boolean(profileId),
        excludedShowIds: options.excludedShowIds ?? [],
        deduplicateAcrossRails: options.deduplicateAcrossRails ?? true,
    });
    const showIds = [
        ...new Set(
            [
                ...classified.fromYourPodcasts,
                ...classified.becauseYouFollowThem,
            ].map(({ showId }) => showId),
        ),
    ];
    if (showIds.length === 0) return rails;

    const shows = await findShowsForHome(
        { id: { in: showIds }, club: { visible: true } },
        [{ date: "asc" }, { id: "asc" }],
        showIds.length,
    );
    const showsById = new Map(shows.map((show) => [show.id, show]));
    rails.fromYourPodcasts.items = classified.fromYourPodcasts.flatMap(
        (item) => {
            const show = showsById.get(item.showId);
            return show ? [{ ...item, show }] : [];
        },
    );
    rails.becauseYouFollowThem.items = classified.becauseYouFollowThem.flatMap(
        (item) => {
            const show = showsById.get(item.showId);
            return show ? [{ ...item, show }] : [];
        },
    );
    return rails;
}
