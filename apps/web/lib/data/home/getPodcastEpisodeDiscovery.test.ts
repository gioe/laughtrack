import { PGlite } from "@electric-sql/pglite";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { $queryRaw: vi.fn() },
}));
vi.mock("@/lib/data/comedian/imageAssets", () => ({
    buildComedianImageUrls: vi.fn(
        ({ name }: { name: string }) => ({
            imageUrl: `https://cdn.example.com/comedians/${name}.jpg`,
        }),
    ),
}));
vi.mock("@/lib/data/podcast/imageUrl", () => ({
    buildPodcastArtworkUrl: vi.fn(
        (url: string | null) =>
            url ? `https://cdn.example.com/podcasts/${url}` : null,
    ),
}));

import { db } from "@/lib/db";
import {
    buildPodcastEpisodeDiscoveryQuery,
    getPodcastEpisodeDiscovery,
    rankPodcastEpisodeDiscoveryCandidates,
    type PodcastEpisodeDiscoveryCandidate,
} from "./getPodcastEpisodeDiscovery";

const mockQueryRaw = vi.mocked(db.$queryRaw);
const NOW = new Date("2026-08-06T12:00:00.000Z");
const RECENT = new Date("2026-08-01T12:00:00.000Z");

type SqlLike = {
    strings: readonly string[];
    values: readonly unknown[];
};

function toPgliteQuery(query: SqlLike) {
    const values = query.values.map((value) =>
        value instanceof Date ? value.toISOString() : value,
    );
    const text = query.strings.reduce((sql, chunk, index) => {
        if (index >= values.length) return sql + chunk;
        return `${sql}${chunk}$${index + 1}`;
    }, "");
    return { text, values };
}

function candidate(
    episodeId: number,
    overrides: Partial<PodcastEpisodeDiscoveryCandidate> = {},
): PodcastEpisodeDiscoveryCandidate {
    return {
        appearanceId: episodeId,
        appearanceRole: "host",
        episodeId,
        episodeGuid: `guid-${episodeId}`,
        episodeTitle: `Episode ${episodeId}`,
        episodeDescription: `<p>Description ${episodeId}</p>`,
        releaseDate: RECENT,
        durationSeconds: 3_600,
        episodeUrl: `https://example.com/episodes/${episodeId}`,
        audioUrl: `https://cdn.example.com/audio/${episodeId}.mp3`,
        podcastId: episodeId,
        podcastSlug: `podcast-${episodeId}`,
        podcastTitle: `Podcast ${episodeId}`,
        podcastAuthorName: `Author ${episodeId}`,
        podcastFeedUrl: `https://feeds.example.com/${episodeId}.xml`,
        podcastImageUrl: `podcast-${episodeId}.jpg`,
        comedianId: episodeId,
        comedianUuid: `comedian-${episodeId}`,
        comedianName: `Comedian ${episodeId}`,
        comedianPopularity: 0.5,
        comedianHasImage: true,
        comedianAvatarPath: null,
        followedComedian: false,
        favoritePodcast: false,
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    mockQueryRaw.mockResolvedValue([]);
});

describe("getPodcastEpisodeDiscovery", () => {
    it("filters ineligible episode candidates", async () => {
        const pg = new PGlite();
        try {
            await pg.exec(`
                CREATE TABLE comedians (
                    id INTEGER PRIMARY KEY,
                    uuid TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    popularity DOUBLE PRECISION NOT NULL DEFAULT 0,
                    has_image BOOLEAN NOT NULL DEFAULT false,
                    visible BOOLEAN NOT NULL DEFAULT true,
                    parent_comedian_id INTEGER REFERENCES comedians(id)
                );
                CREATE TABLE comedian_deny_list (name TEXT PRIMARY KEY);
                CREATE TABLE comedian_image_assets (
                    id INTEGER PRIMARY KEY,
                    comedian_id INTEGER NOT NULL REFERENCES comedians(id),
                    avatar_path TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT true,
                    published_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                CREATE TABLE podcasts (
                    id INTEGER PRIMARY KEY,
                    slug TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_podcast_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    author_name TEXT,
                    feed_url TEXT,
                    image_url TEXT
                );
                CREATE TABLE podcast_deny_list (
                    id INTEGER PRIMARY KEY,
                    podcast_id INTEGER,
                    source TEXT,
                    source_podcast_id TEXT,
                    feed_url TEXT,
                    restored_at TIMESTAMPTZ
                );
                CREATE TABLE podcast_episodes (
                    id INTEGER PRIMARY KEY,
                    podcast_id INTEGER NOT NULL REFERENCES podcasts(id),
                    guid TEXT,
                    title TEXT NOT NULL,
                    description TEXT,
                    release_date TIMESTAMPTZ,
                    duration_seconds INTEGER,
                    episode_url TEXT,
                    audio_url TEXT
                );
                CREATE TABLE episode_appearances (
                    id INTEGER PRIMARY KEY,
                    comedian_id INTEGER NOT NULL REFERENCES comedians(id),
                    episode_id INTEGER NOT NULL REFERENCES podcast_episodes(id),
                    appearance_role TEXT NOT NULL,
                    review_status TEXT NOT NULL
                );
                CREATE TABLE favorite_comedians (
                    profile_id TEXT NOT NULL,
                    comedian_id TEXT NOT NULL
                );
                CREATE TABLE favorite_podcasts (
                    profile_id TEXT NOT NULL,
                    podcast_id INTEGER NOT NULL
                );

                INSERT INTO comedians
                    (id, uuid, name, popularity, visible, parent_comedian_id)
                VALUES
                    (1, 'eligible', 'Eligible Comic', 0.8, true, NULL),
                    (2, 'hidden', 'Hidden Comic', 0.8, false, NULL),
                    (3, 'alias', 'Eligible Alias', 0.8, true, 1),
                    (4, 'denied', E'  DENIED\u00a0  Comic  ', 0.8, true, NULL);
                INSERT INTO comedian_deny_list (name) VALUES ('Denied Comic');

                INSERT INTO podcasts
                    (id, slug, source, source_podcast_id, title, feed_url)
                VALUES
                    (1, 'eligible', 'rss', 'p1', 'Eligible Podcast', 'https://feeds.example.com/1'),
                    (2, 'denied-id', 'rss', 'p2', 'Denied By Id', 'https://feeds.example.com/2'),
                    (3, 'denied-source', 'rss', 'p3', 'Denied By Source', 'https://feeds.example.com/3'),
                    (4, 'denied-feed', 'rss', 'p4', 'Denied By Feed', 'https://feeds.example.com/4'),
                    (5, 'restored', 'rss', 'p5', 'Restored Podcast', 'https://feeds.example.com/5');
                INSERT INTO podcast_deny_list
                    (id, podcast_id, source, source_podcast_id, feed_url, restored_at)
                VALUES
                    (1, 2, NULL, NULL, NULL, NULL),
                    (2, NULL, 'rss', 'p3', NULL, NULL),
                    (3, NULL, NULL, NULL, 'https://feeds.example.com/4', NULL),
                    (4, 5, NULL, NULL, NULL, '2026-08-01T00:00:00Z');

                INSERT INTO podcast_episodes
                    (id, podcast_id, guid, title, release_date, audio_url)
                VALUES
                    (101, 1, '101', 'Eligible', '2026-08-01T00:00:00Z', '101.mp3'),
                    (102, 1, '102', 'Pending', '2026-08-01T00:00:00Z', '102.mp3'),
                    (103, 1, '103', 'Rejected', '2026-08-01T00:00:00Z', '103.mp3'),
                    (104, 1, '104', 'Hidden', '2026-08-01T00:00:00Z', '104.mp3'),
                    (105, 1, '105', 'Alias', '2026-08-01T00:00:00Z', '105.mp3'),
                    (106, 1, '106', 'Denied Comedian', '2026-08-01T00:00:00Z', '106.mp3'),
                    (107, 2, '107', 'Denied Podcast Id', '2026-08-01T00:00:00Z', '107.mp3'),
                    (108, 3, '108', 'Denied Podcast Source', '2026-08-01T00:00:00Z', '108.mp3'),
                    (109, 4, '109', 'Denied Podcast Feed', '2026-08-01T00:00:00Z', '109.mp3'),
                    (110, 5, '110', 'Restored Podcast', '2026-08-01T00:00:00Z', '110.mp3'),
                    (111, 1, '111', 'Stale', '2026-06-01T00:00:00Z', '111.mp3'),
                    (112, 1, '112', 'Future', '2026-08-07T00:00:00Z', '112.mp3');
                INSERT INTO episode_appearances
                    (id, comedian_id, episode_id, appearance_role, review_status)
                VALUES
                    (1, 1, 101, 'guest', 'accepted'),
                    (2, 1, 102, 'guest', 'pending'),
                    (3, 1, 103, 'guest', 'rejected'),
                    (4, 2, 104, 'guest', 'accepted'),
                    (5, 3, 105, 'guest', 'accepted'),
                    (6, 4, 106, 'guest', 'accepted'),
                    (7, 1, 107, 'guest', 'accepted'),
                    (8, 1, 108, 'guest', 'accepted'),
                    (9, 1, 109, 'guest', 'accepted'),
                    (10, 1, 110, 'guest', 'accepted'),
                    (11, 1, 111, 'guest', 'accepted'),
                    (12, 1, 112, 'guest', 'accepted');
            `);

            const query = buildPodcastEpisodeDiscoveryQuery({
                profileId: null,
                cutoff: new Date("2026-07-07T12:00:00.000Z"),
                now: NOW,
                candidateLimit: 200,
            });
            const result = await pg.query<{ episode_id: number }>(
                ...(() => {
                    const converted = toPgliteQuery(query as SqlLike);
                    return [converted.text, converted.values] as const;
                })(),
            );

            expect(result.rows.map((row) => row.episode_id)).toEqual([
                101, 110,
            ]);
        } finally {
            await pg.close();
        }
    });

    it("ranks episode recommendations", async () => {
        const old = new Date("2026-07-10T00:00:00.000Z");
        const newer = new Date("2026-08-05T00:00:00.000Z");
        const inputs = [
            candidate(7, { comedianPopularity: 0.4, releaseDate: newer }),
            candidate(6, { comedianPopularity: 0.4, releaseDate: newer }),
            candidate(5, { comedianPopularity: 0.4, releaseDate: old }),
            candidate(4, { comedianPopularity: 0.9, releaseDate: old }),
            candidate(3, { appearanceRole: "guest", comedianPopularity: 0 }),
            candidate(2, { favoritePodcast: true, comedianPopularity: 0 }),
            candidate(1, {
                followedComedian: true,
                comedianPopularity: 0,
                releaseDate: old,
            }),
        ];

        expect(
            rankPodcastEpisodeDiscoveryCandidates(inputs, 10).map(
                ({ episodeId }) => episodeId,
            ),
        ).toEqual([1, 2, 3, 4, 6, 7, 5]);

        mockQueryRaw.mockResolvedValue([
            {
                appearance_id: 31,
                appearance_role: "co-host",
                episode_id: 30,
                episode_guid: "guid-30",
                episode_title: "Episode Thirty",
                episode_description: "<p>A &amp; B</p>",
                release_date: RECENT,
                duration_seconds: 1_800,
                episode_url: "https://example.com/30",
                audio_url: "https://cdn.example.com/30.mp3",
                podcast_id: 20,
                podcast_slug: "the-podcast",
                podcast_title: "The Podcast",
                podcast_author_name: "The Hosts",
                podcast_feed_url: "https://feeds.example.com/the-podcast",
                podcast_image_url: "the-podcast.jpg",
                comedian_id: 10,
                comedian_uuid: "comic-10",
                comedian_name: "Comic Ten",
                comedian_popularity: 0.8,
                comedian_has_image: true,
                comedian_avatar_path: "comic-10/avatar.jpg",
                followed_comedian: true,
                favorite_podcast: false,
            },
        ] as never);

        await expect(getPodcastEpisodeDiscovery("profile-1")).resolves.toEqual(
            [
                expect.objectContaining({
                    id: 30,
                    description: "A & B",
                    podcast: {
                        id: 20,
                        slug: "the-podcast",
                        title: "The Podcast",
                        imageUrl:
                            "https://cdn.example.com/podcasts/the-podcast.jpg",
                    },
                    recommendation: {
                        reason: "followed_comedian",
                        comedian: {
                            id: 10,
                            uuid: "comic-10",
                            name: "Comic Ten",
                            imageUrl:
                                "https://cdn.example.com/comedians/Comic Ten.jpg",
                        },
                        appearanceRole: "cohost",
                        followedComedian: true,
                        favoritePodcast: false,
                    },
                }),
            ],
        );
    });

    it("deduplicates and diversifies recommendations", () => {
        const sameFeed = "https://feeds.example.com/show.xml";
        const inputs = [
            candidate(1, {
                episodeGuid: "shared-guid",
                podcastId: 1,
                podcastFeedUrl: sameFeed,
                comedianId: 1,
            }),
            candidate(99, {
                episodeGuid: " SHARED-GUID ",
                podcastId: 99,
                podcastFeedUrl: `${sameFeed}/`,
                comedianId: 1,
                followedComedian: true,
            }),
            candidate(2, {
                podcastId: 1,
                podcastFeedUrl: sameFeed,
                comedianId: 2,
            }),
            candidate(3, {
                podcastId: 2,
                podcastFeedUrl: sameFeed,
                comedianId: 3,
            }),
            candidate(4, {
                podcastId: 3,
                comedianId: 1,
            }),
            candidate(5, {
                podcastId: 4,
                comedianId: 1,
            }),
            candidate(6, {
                podcastId: 5,
                comedianId: 4,
            }),
        ];

        expect(
            rankPodcastEpisodeDiscoveryCandidates(inputs, 6).map(
                ({ episodeId }) => episodeId,
            ),
        ).toEqual([99, 2, 4, 6]);

        const sameTimestampDistinctEpisodes = [
            candidate(10, { episodeGuid: "distinct-a" }),
            candidate(11, {
                episodeGuid: "distinct-b",
                podcastId: 10,
                podcastFeedUrl: "https://feeds.example.com/10.xml",
            }),
        ];
        expect(
            rankPodcastEpisodeDiscoveryCandidates(
                sameTimestampDistinctEpisodes,
                2,
            ),
        ).toHaveLength(2);

        const audioDuplicates = [
            candidate(20, {
                episodeGuid: null,
                audioUrl: "https://cdn.example.com/shared.mp3",
            }),
            candidate(21, {
                episodeGuid: null,
                audioUrl: "HTTPS://CDN.EXAMPLE.COM/shared.mp3/",
            }),
        ];
        expect(
            rankPodcastEpisodeDiscoveryCandidates(audioDuplicates, 2),
        ).toHaveLength(1);

        const fallbackDuplicates = [
            candidate(30, {
                episodeGuid: null,
                audioUrl: null,
                episodeTitle: "Ep 12 - Same Episode",
            }),
            candidate(31, {
                episodeGuid: null,
                audioUrl: null,
                episodeTitle: "12 - Same Episode",
                podcastId: 30,
                podcastFeedUrl: "https://feeds.example.com/30.xml",
            }),
        ];
        expect(
            rankPodcastEpisodeDiscoveryCandidates(fallbackDuplicates, 2),
        ).toHaveLength(1);
    });
});
