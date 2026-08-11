import { PGlite } from "@electric-sql/pglite";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { $queryRaw: vi.fn() },
}));
vi.mock("./findShowsForHome", () => ({
    findShowsForHome: vi.fn(),
}));

import { db } from "@/lib/db";
import { findShowsForHome } from "./findShowsForHome";
import {
    buildAffinityQuery,
    classifyAffinityCandidates,
    getAffinityRails,
    type AffinityEvidenceRow,
} from "./getAffinityRails";

const NOW = new Date("2026-08-07T12:00:00.000Z");
const UPCOMING = new Date("2026-08-20T20:00:00.000Z");
const REQUEST = {
    now: NOW,
    horizonDays: 90,
    limit: 8,
    personalized: true,
    excludedShowIds: [],
} as const;

const mockQueryRaw = vi.mocked(db.$queryRaw);
const mockFindShowsForHome = vi.mocked(findShowsForHome);

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

function row(
    showId: number,
    canonicalComedianId: number,
    overrides: Partial<AffinityEvidenceRow> = {},
): AffinityEvidenceRow {
    return {
        showId,
        showDate: new Date(UPCOMING.getTime() + showId * 1_000),
        showName: `Show ${showId}`,
        clubVisible: true,
        performerVisible: true,
        canonicalVisible: true,
        ticketsSoldOut: false,
        hasPurchasePath: true,
        canonicalComedianId,
        canonicalComedianUuid: `comic-${canonicalComedianId}`,
        canonicalComedianName: `Comic ${canonicalComedianId}`,
        podcastId: null,
        podcastSlug: null,
        podcastTitle: null,
        podcastAttribution: null,
        appearanceRole: null,
        episodeId: null,
        episodeTitle: null,
        episodeReleaseDate: null,
        ...overrides,
    };
}

function podcastRow(
    showId: number,
    canonicalComedianId: number,
    overrides: Partial<AffinityEvidenceRow> = {},
): AffinityEvidenceRow {
    return row(showId, canonicalComedianId, {
        podcastId: 10,
        podcastSlug: "favorite-podcast",
        podcastTitle: "Favorite Podcast",
        podcastAttribution: "host",
        ...overrides,
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockQueryRaw.mockResolvedValue([]);
    mockFindShowsForHome.mockResolvedValue([]);
});

async function buildFixture() {
    const database = new PGlite();
    await database.exec(`
        CREATE TABLE clubs (id INTEGER PRIMARY KEY, visible BOOLEAN NOT NULL);
        CREATE TABLE shows (
            id INTEGER PRIMARY KEY,
            date TIMESTAMPTZ NOT NULL,
            name TEXT,
            club_id INTEGER NOT NULL,
            tickets_sold_out BOOLEAN NOT NULL
        );
        CREATE TABLE tickets (
            id INTEGER PRIMARY KEY,
            show_id INTEGER NOT NULL,
            sold_out BOOLEAN NOT NULL,
            purchase_url TEXT
        );
        CREATE TABLE comedians (
            id INTEGER PRIMARY KEY,
            uuid TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            visible BOOLEAN NOT NULL,
            parent_comedian_id INTEGER
        );
        CREATE TABLE lineup_items (show_id INTEGER NOT NULL, comedian_id TEXT NOT NULL);
        CREATE TABLE comedian_deny_list (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE tags (id INTEGER PRIMARY KEY, "restrictContent" BOOLEAN NOT NULL);
        CREATE TABLE tagged_comedians (tag_id INTEGER NOT NULL, comedian_id TEXT NOT NULL);
        CREATE TABLE favorite_comedians (profile_id TEXT NOT NULL, comedian_id TEXT NOT NULL);
        CREATE TABLE podcasts (
            id INTEGER PRIMARY KEY,
            slug TEXT NOT NULL,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            source_podcast_id TEXT NOT NULL,
            feed_url TEXT
        );
        CREATE TABLE favorite_podcasts (profile_id TEXT NOT NULL, podcast_id INTEGER NOT NULL);
        CREATE TABLE podcast_deny_list (
            id INTEGER PRIMARY KEY,
            podcast_id INTEGER,
            source TEXT,
            source_podcast_id TEXT,
            feed_url TEXT,
            restored_at TIMESTAMPTZ
        );
        CREATE TABLE comedian_podcasts (
            id INTEGER PRIMARY KEY,
            comedian_id INTEGER NOT NULL,
            podcast_id INTEGER NOT NULL,
            association_type TEXT NOT NULL,
            review_status TEXT NOT NULL
        );
        CREATE TABLE podcast_episodes (
            id INTEGER PRIMARY KEY,
            podcast_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            release_date TIMESTAMPTZ
        );
        CREATE TABLE episode_appearances (
            id INTEGER PRIMARY KEY,
            comedian_id INTEGER NOT NULL,
            episode_id INTEGER NOT NULL,
            appearance_role TEXT NOT NULL,
            review_status TEXT NOT NULL
        );

        INSERT INTO clubs VALUES (1, true);
        INSERT INTO shows VALUES
            (101, '2026-08-20T20:00:00Z', 'Host show', 1, false),
            (102, '2026-08-21T20:00:00Z', 'Guest show', 1, false),
            (103, '2026-08-22T20:00:00Z', 'Stacked show', 1, false),
            (104, '2026-08-23T20:00:00Z', 'Followed show', 1, false);
        INSERT INTO tickets VALUES
            (1, 101, false, 'https://tickets/101'),
            (2, 102, false, 'https://tickets/102'),
            (3, 103, false, 'https://tickets/103'),
            (4, 104, false, 'https://tickets/104');
        INSERT INTO comedians VALUES
            (1, 'host', 'Host Comic', true, NULL),
            (2, 'guest', 'Guest Comic', true, NULL),
            (3, 'host-alias', 'Host Alias', true, 1),
            (4, 'followed', 'Followed Comic', true, NULL),
            (5, 'denied', 'Denied Comic', true, NULL);
        INSERT INTO lineup_items VALUES
            (101, 'host'), (101, 'host-alias'),
            (102, 'guest'),
            (103, 'host'), (103, 'guest'), (103, 'followed'),
            (104, 'followed');
        INSERT INTO favorite_comedians VALUES ('profile-1', 'followed');
        INSERT INTO podcasts VALUES
            (10, 'favorite', 'Favorite Podcast', 'apple', '10', 'https://feeds/10'),
            (11, 'denied-podcast', 'Denied Podcast', 'apple', '11', 'https://feeds/11');
        INSERT INTO favorite_podcasts VALUES ('profile-1', 10), ('profile-1', 11);
        INSERT INTO podcast_deny_list VALUES
            (1, 11, 'apple', '11', 'https://feeds/11', NULL);
        INSERT INTO comedian_podcasts VALUES
            (1, 3, 10, 'host', 'accepted'),
            (2, 4, 10, 'host', 'pending'),
            (3, 4, 11, 'host', 'accepted');
        INSERT INTO podcast_episodes VALUES
            (201, 10, 'Recent episode', '2026-08-01T12:00:00Z'),
            (202, 10, 'Old episode', '2026-06-01T12:00:00Z');
        INSERT INTO episode_appearances VALUES
            (1, 2, 201, 'guest', 'accepted'),
            (2, 4, 201, 'guest', 'pending'),
            (3, 4, 202, 'guest', 'accepted');
    `);
    return database;
}

describe("getAffinityRails", () => {
    it("from your podcasts uses only accepted host/cohost or accepted recent appearance evidence from favorite podcasts", async () => {
        const database = await buildFixture();
        try {
            const query = buildAffinityQuery({
                profileId: "profile-1",
                now: NOW,
                horizonEnd: new Date("2026-11-05T12:00:00.000Z"),
                appearanceCutoff: new Date("2026-07-08T12:00:00.000Z"),
            });
            const result = await database.query<{
                show_id: number;
                canonical_comedian_id: number;
                podcast_id: number | null;
                podcast_attribution: string | null;
                episode_id: number | null;
            }>(...(Object.values(toPgliteQuery(query)) as [string, unknown[]]));

            const host = result.rows.find(
                (candidate) =>
                    candidate.show_id === 101 &&
                    candidate.canonical_comedian_id === 1,
            );
            const guest = result.rows.find(
                (candidate) =>
                    candidate.show_id === 102 &&
                    candidate.canonical_comedian_id === 2,
            );
            const pendingOrStale = result.rows.find(
                (candidate) =>
                    candidate.show_id === 104 && candidate.podcast_id !== null,
            );

            expect(host).toMatchObject({
                podcast_id: 10,
                podcast_attribution: "host",
                episode_id: null,
            });
            expect(guest).toMatchObject({
                podcast_id: 10,
                podcast_attribution: "recent_appearance",
                episode_id: 201,
            });
            expect(pendingOrStale).toBeUndefined();

            const classified = classifyAffinityCandidates(
                result.rows.map((candidate) =>
                    row(candidate.show_id, candidate.canonical_comedian_id, {
                        podcastId: candidate.podcast_id,
                        podcastSlug:
                            candidate.podcast_id === null ? null : "favorite",
                        podcastTitle:
                            candidate.podcast_id === null
                                ? null
                                : "Favorite Podcast",
                        podcastAttribution: candidate.podcast_attribution,
                        episodeId: candidate.episode_id,
                        episodeTitle:
                            candidate.episode_id === null
                                ? null
                                : "Recent episode",
                        episodeReleaseDate:
                            candidate.episode_id === null
                                ? null
                                : new Date("2026-08-01T12:00:00.000Z"),
                    }),
                ),
                REQUEST,
            );
            expect(
                classified.fromYourPodcasts.map(({ showId }) => showId),
            ).toEqual([101, 102, 103]);
            expect(JSON.stringify(classified)).not.toContain("profile-1");
        } finally {
            await database.close();
        }
    });

    it("keeps podcast affinity private for anonymous users", async () => {
        const anonymous = classifyAffinityCandidates(
            [podcastRow(301, 1), row(301, 2), row(301, 3)],
            { ...REQUEST, personalized: false },
        );
        expect(anonymous.fromYourPodcasts).toEqual([]);

        mockQueryRaw.mockResolvedValue([
            {
                show_id: 301,
                show_date: UPCOMING,
                show_name: "Anonymous show",
                club_visible: true,
                performer_visible: true,
                canonical_visible: true,
                tickets_sold_out: false,
                has_purchase_path: true,
                canonical_comedian_id: 1,
                canonical_comedian_uuid: "comic-1",
                canonical_comedian_name: "Comic 1",
                podcast_id: 10,
                podcast_slug: "favorite",
                podcast_title: "Favorite Podcast",
                podcast_attribution: "host",
                appearance_role: null,
                episode_id: null,
                episode_title: null,
                episode_release_date: null,
            },
            ...[2, 3].map((id) => ({
                show_id: 301,
                show_date: UPCOMING,
                show_name: "Anonymous stacked show",
                club_visible: true,
                performer_visible: true,
                canonical_visible: true,
                tickets_sold_out: false,
                has_purchase_path: true,
                canonical_comedian_id: id,
                canonical_comedian_uuid: `comic-${id}`,
                canonical_comedian_name: `Comic ${id}`,
                podcast_id: null,
                podcast_slug: null,
                podcast_title: null,
                podcast_attribution: null,
                appearance_role: null,
                episode_id: null,
                episode_title: null,
                episode_release_date: null,
            })),
        ] as never);
        const result = await getAffinityRails(null, { now: NOW });
        expect(result.fromYourPodcasts.items).toEqual([]);
        expect(mockFindShowsForHome).not.toHaveBeenCalled();
    });

    it("canonical aliases merge evidence and excluded shows stay excluded", () => {
        const candidates = [
            podcastRow(401, 1),
            row(401, 1, {
                canonicalComedianUuid: "alias-of-1",
            }),
            row(401, 2),
            row(401, 3),
            podcastRow(404, 5),
        ];

        const selected = classifyAffinityCandidates(candidates, {
            ...REQUEST,
            excludedShowIds: [404],
        });

        expect(selected.fromYourPodcasts.map(({ showId }) => showId)).toEqual([
            401,
        ]);
    });
});
