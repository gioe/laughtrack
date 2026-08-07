import { PGlite } from "@electric-sql/pglite";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { $queryRaw: vi.fn() },
}));
vi.mock("./findShowsForHome", () => ({
    findShowsForHome: vi.fn(),
}));

import { db } from "@/lib/db";
import { DISCOVERY_FEATURE_VERSION } from "@/lib/discovery/features";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { findShowsForHome } from "./findShowsForHome";
import {
    buildFreshAndRisingQuery,
    classifyFreshAndRisingCandidates,
    getFreshAndRisingRails,
    type FreshAndRisingEvidenceRow,
} from "./getFreshAndRisingRails";

const NOW = new Date("2026-08-07T12:00:00.000Z");
const UPCOMING = new Date("2026-08-20T20:00:00.000Z");
const REQUEST = { now: NOW, horizonDays: 90, limit: 8 } as const;

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

function signals() {
    return {
        windows: {},
        behavior: {
            momentumWindow: "recent",
            recentImpressionActors: 40,
            baselineImpressionActors: 30,
            trailing28ImpressionActors: 70,
            recentDetailActors: 7,
            baselineDetailActors: 3,
            recentTicketIntentActors: 4,
            baselineTicketIntentActors: 1,
            recentDemandActors: 10,
            baselineDemandActors: 4,
            recentDemandRate: 0.25,
            baselineDemandRate: 0.13,
            growth: 0.5,
            confidence: 1,
        },
        favorites: {
            recentCount: 8,
            baselineCount: 4,
            recentDailyRate: 1.14,
            baselineDailyRate: 0.14,
            growth: 0.75,
            confidence: 1,
        },
        social: {
            pairedSeries: 3,
            observedSeries: 3,
            growth: 0.4,
            confidence: 1,
        },
        confidenceReasons: [],
    };
}

function row(
    overrides: Partial<FreshAndRisingEvidenceRow> = {},
): FreshAndRisingEvidenceRow {
    return {
        showId: 101,
        showDate: UPCOMING,
        showName: "Fresh Show",
        firstDiscoveredAt: new Date("2026-08-05T12:00:00.000Z"),
        clubVisible: true,
        performerVisible: true,
        canonicalVisible: true,
        ticketsSoldOut: false,
        hasPurchasePath: true,
        canonicalComedianId: 10,
        canonicalComedianUuid: "canonical-comic",
        canonicalComedianName: "Canonical Comic",
        featureVersion: DISCOVERY_FEATURE_VERSION,
        featureAsOf: new Date("2026-08-07T00:00:00.000Z"),
        prominence: 0.35,
        momentum: 0.25,
        growth: 0.75,
        confidence: 0.8,
        availability: "available",
        featureEvidence: signals(),
        ...overrides,
    };
}

function rawRow(overrides: Record<string, unknown> = {}) {
    return {
        show_id: 101,
        show_date: UPCOMING,
        show_name: "Fresh Show",
        first_discovered_at: new Date("2026-08-05T12:00:00.000Z"),
        club_visible: true,
        performer_visible: true,
        canonical_visible: true,
        tickets_sold_out: false,
        has_purchase_path: true,
        canonical_comedian_id: 10,
        canonical_comedian_uuid: "canonical-comic",
        canonical_comedian_name: "Canonical Comic",
        feature_version: DISCOVERY_FEATURE_VERSION,
        feature_as_of: new Date("2026-08-07T00:00:00.000Z"),
        prominence: 0.35,
        momentum: 0.25,
        growth: 0.75,
        confidence: 0.8,
        availability: "available",
        feature_evidence: signals(),
        ...overrides,
    };
}

function show(id = 101): ShowDTO {
    return {
        id,
        clubId: 5,
        clubName: "Local Club",
        date: UPCOMING,
        name: "Fresh Show",
        imageUrl: "https://example.com/show.jpg",
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    mockQueryRaw.mockResolvedValue([]);
    mockFindShowsForHome.mockResolvedValue([]);
});

describe("getFreshAndRisingRails", () => {
    it("newly added uses firstDiscoveredAt and distinguishes observation from verified announcement provenance", () => {
        const selected = classifyFreshAndRisingCandidates([row()], REQUEST);
        expect(selected.newlyAdded[0].reason).toMatchObject({
            kind: "newly_added",
            label: "Newly found by LaughTrack",
            evidence: {
                firstDiscoveredAt: new Date("2026-08-05T12:00:00.000Z"),
                freshnessProvenance: { kind: "laughtrack_observation" },
            },
        });

        const unverified = classifyFreshAndRisingCandidates(
            [
                row({
                    announcementProvenance: {
                        verified: false,
                        source: "Venue",
                        announcedAt: new Date("2026-08-04T00:00:00.000Z"),
                    },
                }),
            ],
            REQUEST,
        );
        expect(unverified.newlyAdded[0].reason.label).toBe(
            "Newly found by LaughTrack",
        );

        const verified = classifyFreshAndRisingCandidates(
            [
                row({
                    announcementProvenance: {
                        verified: true,
                        source: "The Venue",
                        announcedAt: new Date("2026-08-04T00:00:00.000Z"),
                    },
                }),
            ],
            REQUEST,
        );
        expect(verified.newlyAdded[0].reason).toMatchObject({
            label: "Recently announced by The Venue",
            evidence: {
                freshnessProvenance: {
                    kind: "verified_announcement",
                    source: "The Venue",
                },
            },
        });

        for (const candidate of [
            row({ firstDiscoveredAt: null }),
            row({
                firstDiscoveredAt: new Date("2026-07-01T00:00:00.000Z"),
            }),
            row({
                firstDiscoveredAt: new Date("2026-08-08T00:00:00.000Z"),
            }),
        ]) {
            expect(
                classifyFreshAndRisingCandidates([candidate], REQUEST)
                    .newlyAdded,
            ).toEqual([]);
        }
    });

    it("starting to buzz requires confident positive momentum or growth and returns structured supporting evidence", () => {
        const selected = classifyFreshAndRisingCandidates([row()], REQUEST);
        expect(selected.startingToBuzz[0].reason).toMatchObject({
            kind: "starting_to_buzz",
            evidence: {
                featureVersion: DISCOVERY_FEATURE_VERSION,
                momentum: 0.25,
                growth: 0.75,
                confidence: 0.8,
                signals: {
                    behavior: {
                        recentDetailActors: 7,
                        recentTicketIntentActors: 4,
                        recentDemandActors: 10,
                    },
                    favorites: { recentCount: 8, growth: 0.75 },
                    social: { pairedSeries: 3, growth: 0.4 },
                },
            },
        });

        const momentumOnly = row({ growth: 0.5 });
        expect(
            classifyFreshAndRisingCandidates([momentumOnly], REQUEST)
                .startingToBuzz,
        ).toHaveLength(1);

        for (const candidate of [
            row({ momentum: 0.14, growth: 0.59 }),
            row({ confidence: 0.49 }),
            row({ momentum: 0.9, growth: 0.9, featureEvidence: {} }),
        ]) {
            expect(
                classifyFreshAndRisingCandidates([candidate], REQUEST)
                    .startingToBuzz,
            ).toEqual([]);
        }
    });

    it("catch them early favors growing lower-prominence performers without letting prominence define eligibility", () => {
        const lowerProminence = row({ showId: 201, prominence: 0.1 });
        const higherProminence = row({ showId: 202, prominence: 0.55 });
        const selected = classifyFreshAndRisingCandidates(
            [higherProminence, lowerProminence],
            REQUEST,
        );
        expect(selected.catchThemEarly.map(({ showId }) => showId)).toEqual([
            201, 202,
        ]);
        expect(selected.catchThemEarly[0].reason).toMatchObject({
            kind: "catch_them_early",
            evidence: { prominence: 0.1, growth: 0.75 },
        });

        expect(
            classifyFreshAndRisingCandidates(
                [row({ prominence: 0.95, growth: 0.95 })],
                REQUEST,
            ).catchThemEarly,
        ).toHaveLength(1);
        expect(
            classifyFreshAndRisingCandidates(
                [row({ prominence: 0.01, growth: 0.5, momentum: 0.5 })],
                REQUEST,
            ).catchThemEarly,
        ).toEqual([]);
    });

    it("suppresses stale, sparse, unavailable, past, sold-out, hidden, and unactionable candidates", () => {
        const invalidRows: FreshAndRisingEvidenceRow[] = [
            row({ showId: 201, clubVisible: false }),
            row({ showId: 202, performerVisible: false }),
            row({ showId: 203, canonicalVisible: false }),
            row({ showId: 204, ticketsSoldOut: true }),
            row({ showId: 205, showName: "SOLD OUT show" }),
            row({ showId: 206, hasPurchasePath: false }),
            row({
                showId: 207,
                showDate: new Date("2026-08-01T00:00:00.000Z"),
            }),
            row({ showId: 208, availability: "unavailable" }),
        ];
        const selected = classifyFreshAndRisingCandidates(invalidRows, REQUEST);
        expect(selected.newlyAdded).toEqual([]);
        expect(selected.startingToBuzz).toEqual([]);
        expect(selected.catchThemEarly).toEqual([]);

        for (const candidate of [
            row({
                firstDiscoveredAt: null,
                featureVersion: "old-version",
            }),
            row({
                firstDiscoveredAt: null,
                featureAsOf: new Date("2026-08-04T00:00:00.000Z"),
            }),
            row({ firstDiscoveredAt: null, confidence: 0.1 }),
            row({ firstDiscoveredAt: null, featureEvidence: null }),
        ]) {
            const result = classifyFreshAndRisingCandidates(
                [candidate],
                REQUEST,
            );
            expect(result.startingToBuzz).toEqual([]);
            expect(result.catchThemEarly).toEqual([]);
        }

        const neutralMissingSnapshot = classifyFreshAndRisingCandidates(
            [
                row({
                    featureVersion: null,
                    featureAsOf: null,
                    prominence: null,
                    momentum: null,
                    growth: null,
                    confidence: null,
                    availability: null,
                    featureEvidence: null,
                }),
            ],
            REQUEST,
        );
        expect(neutralMissingSnapshot.newlyAdded).toHaveLength(1);
        expect(neutralMissingSnapshot.startingToBuzz).toEqual([]);
        expect(neutralMissingSnapshot.catchThemEarly).toEqual([]);
    });

    it("builds a current-version, visible, canonical, actionable evidence query", () => {
        const query = buildFreshAndRisingQuery({
            now: NOW,
            horizonEnd: new Date("2026-11-05T12:00:00.000Z"),
        });
        const sql = query.strings.join("?");

        expect(sql).toContain("s.first_discovered_at");
        expect(sql).toContain("club.visible = true");
        expect(sql).toContain("performer.visible = true");
        expect(sql).toContain("canonical.visible = true");
        expect(sql).toContain("canonical.parent_comedian_id IS NULL");
        expect(sql).toContain('tag."restrictContent" = true');
        expect(sql).toContain("s.tickets_sold_out = false");
        expect(sql).toContain("ticket.sold_out = false");
        expect(sql).toContain("NULLIF(btrim(ticket.purchase_url), '')");
        expect(sql).toContain("s.first_discovered_at >=");
        expect(sql).toContain("candidate_snapshot.feature_version =");
        expect(sql).toContain("candidate_snapshot.confidence >=");
        expect(sql).toContain("candidate_snapshot.momentum >=");
        expect(sql).toContain("candidate_snapshot.growth >=");
        expect(sql).toContain("ORDER BY snapshot.as_of DESC");
        expect(query.values).toContain(DISCOVERY_FEATURE_VERSION);
    });

    it("executes the evidence query against relational shows and latest snapshots", async () => {
        const pg = new PGlite();
        try {
            await pg.exec(`
                CREATE TABLE clubs (id INTEGER PRIMARY KEY, visible BOOLEAN NOT NULL);
                CREATE TABLE shows (
                    id INTEGER PRIMARY KEY,
                    club_id INTEGER NOT NULL REFERENCES clubs(id),
                    date TIMESTAMPTZ NOT NULL,
                    name TEXT,
                    first_discovered_at TIMESTAMPTZ,
                    tickets_sold_out BOOLEAN NOT NULL
                );
                CREATE TABLE tickets (
                    id INTEGER PRIMARY KEY,
                    show_id INTEGER NOT NULL REFERENCES shows(id),
                    sold_out BOOLEAN NOT NULL,
                    purchase_url TEXT
                );
                CREATE TABLE comedians (
                    id INTEGER PRIMARY KEY,
                    uuid TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    parent_comedian_id INTEGER REFERENCES comedians(id),
                    visible BOOLEAN NOT NULL,
                    popularity DOUBLE PRECISION NOT NULL
                );
                CREATE TABLE lineup_items (show_id INTEGER NOT NULL, comedian_id TEXT NOT NULL);
                CREATE TABLE tags (id INTEGER PRIMARY KEY, "restrictContent" BOOLEAN NOT NULL);
                CREATE TABLE tagged_comedians (comedian_id TEXT NOT NULL, tag_id INTEGER NOT NULL);
                CREATE TABLE discovery_show_feature_snapshots (
                    id BIGINT PRIMARY KEY,
                    show_id INTEGER NOT NULL REFERENCES shows(id),
                    feature_version TEXT NOT NULL,
                    as_of TIMESTAMPTZ NOT NULL,
                    prominence DOUBLE PRECISION NOT NULL,
                    momentum DOUBLE PRECISION NOT NULL,
                    growth DOUBLE PRECISION NOT NULL,
                    confidence DOUBLE PRECISION NOT NULL,
                    availability TEXT NOT NULL,
                    evidence JSONB NOT NULL,
                    computed_at TIMESTAMPTZ NOT NULL
                );

                INSERT INTO clubs VALUES (1, true);
                INSERT INTO shows VALUES (
                    101, 1, '2026-08-20T20:00:00Z', 'Fresh Show',
                    '2026-08-05T12:00:00Z', false
                );
                INSERT INTO tickets VALUES (1, 101, false, 'https://tickets.example/101');
                INSERT INTO comedians VALUES (
                    10, 'canonical-comic', 'Canonical Comic', NULL, true, 0.4
                );
                INSERT INTO lineup_items VALUES (101, 'canonical-comic');
                INSERT INTO discovery_show_feature_snapshots VALUES
                    (1, 101, '${DISCOVERY_FEATURE_VERSION}', '2026-08-06T00:00:00Z', 0.3, 0.2, 0.6, 0.7, 'available', '${JSON.stringify(signals())}', '2026-08-06T00:05:00Z'),
                    (2, 101, '${DISCOVERY_FEATURE_VERSION}', '2026-08-07T00:00:00Z', 0.35, 0.25, 0.75, 0.8, 'available', '${JSON.stringify(signals())}', '2026-08-07T00:05:00Z');
            `);

            const result = await pg.query(
                ...(Object.values(
                    toPgliteQuery(
                        buildFreshAndRisingQuery({
                            now: NOW,
                            horizonEnd: new Date("2026-11-05T12:00:00.000Z"),
                        }),
                    ),
                ) as [string, unknown[]]),
            );
            expect(result.rows).toHaveLength(1);
            expect(result.rows[0]).toMatchObject({
                show_id: 101,
                canonical_comedian_id: 10,
                feature_as_of: new Date("2026-08-07T00:00:00.000Z"),
                growth: 0.75,
            });
        } finally {
            await pg.close();
        }
    });

    it("hydrates selected show DTOs and preserves structured reasons", async () => {
        mockQueryRaw.mockResolvedValue([rawRow()]);
        mockFindShowsForHome.mockResolvedValue([show()]);

        const rails = await getFreshAndRisingRails({ now: NOW });

        expect(mockFindShowsForHome).toHaveBeenCalledWith(
            { id: { in: [101] }, club: { visible: true } },
            [{ date: "asc" }, { id: "asc" }],
            1,
        );
        expect(rails.newlyAdded.items[0]).toMatchObject({
            show: { id: 101 },
            performer: { id: 10, uuid: "canonical-comic" },
            reason: { kind: "newly_added" },
        });
        expect(rails.startingToBuzz.items[0].reason.evidence.signals).toEqual(
            expect.objectContaining({
                favorites: expect.objectContaining({ recentCount: 8 }),
            }),
        );
        expect(rails.catchThemEarly.items).toHaveLength(1);
    });
});
