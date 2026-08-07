import { PGlite } from "@electric-sql/pglite";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { $queryRaw: vi.fn() },
}));
vi.mock("@/util/location/resolveNearbyZips", () => ({
    resolveNearbyZips: vi.fn(() => ["94103", "94107"]),
}));
vi.mock("./findShowsForHome", () => ({
    findShowsForHome: vi.fn(),
}));

import { db } from "@/lib/db";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { findShowsForHome } from "./findShowsForHome";
import {
    buildTouringScarcityQuery,
    classifyTouringScarcityCandidates,
    getTouringScarcityRails,
    type TouringScarcityEvidenceRow,
} from "./getTouringScarcityRails";

const NOW = new Date("2026-08-01T12:00:00.000Z");
const UPCOMING = new Date("2026-08-10T20:00:00.000Z");
const REQUEST = {
    now: NOW,
    horizonDays: 90,
    nearbyZips: ["94103", "94107"],
    requestedMarket: {
        city: "San Francisco",
        state: "CA",
        country: "US",
    },
    limit: 8,
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
    overrides: Partial<TouringScarcityEvidenceRow> = {},
): TouringScarcityEvidenceRow {
    return {
        showId: 101,
        showDate: UPCOMING,
        showName: "Tour Show",
        clubVisible: true,
        performerVisible: true,
        canonicalVisible: true,
        withinRadius: true,
        ticketsSoldOut: false,
        hasPurchasePath: true,
        canonicalComedianId: 10,
        canonicalComedianUuid: "canonical-comic",
        canonicalComedianName: "Canonical Comic",
        homeCity: "Los Angeles",
        homeState: "CA",
        homeCountry: "US",
        homeZipCode: "90001",
        homeLocationUpdatedAt: new Date("2026-07-01T00:00:00.000Z"),
        localAppearanceCount: 1,
        runStart: UPCOMING,
        runEnd: UPCOMING,
        priorLocalAppearanceCount: 1,
        lastLocalAppearanceAt: new Date("2025-01-01T00:00:00.000Z"),
        historyCoverageStart: new Date("2024-01-01T00:00:00.000Z"),
        historyCoverageShowCount: 40,
        ...overrides,
    };
}

function show(id = 101): ShowDTO {
    return {
        id,
        clubId: 5,
        clubName: "Local Club",
        date: UPCOMING,
        name: "Tour Show",
        imageUrl: "https://example.com/show.jpg",
    };
}

function rawRow(overrides: Record<string, unknown> = {}) {
    return {
        show_id: 101,
        show_date: UPCOMING,
        show_name: "Tour Show",
        club_visible: true,
        performer_visible: true,
        canonical_visible: true,
        within_radius: true,
        tickets_sold_out: false,
        has_purchase_path: true,
        canonical_comedian_id: 10,
        canonical_comedian_uuid: "canonical-comic",
        canonical_comedian_name: "Canonical Comic",
        home_city: "Los Angeles",
        home_state: "CA",
        home_country: "US",
        home_zip_code: "90001",
        home_location_updated_at: new Date("2026-07-01T00:00:00.000Z"),
        local_appearance_count: 1,
        run_start: UPCOMING,
        run_end: UPCOMING,
        prior_local_appearance_count: 1,
        last_local_appearance_at: new Date("2025-01-01T00:00:00.000Z"),
        history_coverage_start: new Date("2024-01-01T00:00:00.000Z"),
        history_coverage_show_count: 40,
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    mockQueryRaw.mockResolvedValue([]);
    mockFindShowsForHome.mockResolvedValue([]);
});

describe("getTouringScarcityRails", () => {
    it("just passing through requires a fresh known home outside the requested market and a short run", () => {
        const selected = classifyTouringScarcityCandidates([row()], REQUEST);
        expect(selected.justPassingThrough).toHaveLength(1);
        expect(selected.justPassingThrough[0]).toMatchObject({
            performer: {
                id: 10,
                uuid: "canonical-comic",
                name: "Canonical Comic",
            },
            reason: {
                kind: "just_passing_through",
                label: "Visiting from Los Angeles, CA for 1 local date",
                evidence: {
                    localAppearanceCount: 1,
                    homeMarket: { city: "Los Angeles", state: "CA" },
                    requestedMarket: { city: "San Francisco", state: "CA" },
                },
            },
        });

        const sameMarket = row({ homeZipCode: "94103" });
        const unknownHome = row({
            homeCity: null,
            homeLocationUpdatedAt: null,
        });
        const staleHome = row({
            homeLocationUpdatedAt: new Date("2023-01-01T00:00:00.000Z"),
        });
        const longRun = row({
            localAppearanceCount: 4,
            runEnd: new Date("2026-08-20T20:00:00.000Z"),
        });
        for (const candidate of [sameMarket, unknownHome, staleHome, longRun]) {
            expect(
                classifyTouringScarcityCandidates([candidate], REQUEST)
                    .justPassingThrough,
            ).toEqual([]);
        }
    });

    it("rare return labels require trustworthy local history and never infer first-ever appearances", () => {
        const back = classifyTouringScarcityCandidates([row()], REQUEST);
        expect(back.rareReturns).toHaveLength(1);
        expect(back.rareReturns[0].reason).toMatchObject({
            kind: "back_after_a_while",
            label: expect.stringMatching(/^Back nearby after \d+ months$/),
            evidence: {
                priorLocalAppearanceCount: 1,
                lastLocalAppearanceAt: new Date("2025-01-01T00:00:00.000Z"),
                historyCoverageShowCount: 40,
            },
        });

        const rare = classifyTouringScarcityCandidates(
            [
                row({
                    lastLocalAppearanceAt: new Date("2026-07-01T00:00:00.000Z"),
                    priorLocalAppearanceCount: 2,
                }),
            ],
            REQUEST,
        );
        expect(rare.rareReturns[0].reason.kind).toBe("rare_return");
        expect(rare.rareReturns[0].reason.label).toContain(
            "LaughTrack history",
        );

        const insufficientSpan = row({
            historyCoverageStart: new Date("2026-01-01T00:00:00.000Z"),
        });
        const insufficientInventory = row({ historyCoverageShowCount: 9 });
        const noObservedHistory = row({
            priorLocalAppearanceCount: 0,
            lastLocalAppearanceAt: null,
        });
        for (const candidate of [
            insufficientSpan,
            insufficientInventory,
            noObservedHistory,
        ]) {
            expect(
                classifyTouringScarcityCandidates([candidate], REQUEST)
                    .rareReturns,
            ).toEqual([]);
        }
    });

    it("only chance requires exactly one qualifying local appearance in the horizon", () => {
        expect(
            classifyTouringScarcityCandidates([row()], REQUEST)
                .onlyChanceNearby[0].reason,
        ).toMatchObject({
            kind: "only_chance_nearby",
            label: "Only local date in the next 90 days",
            evidence: { localAppearanceCount: 1, horizonDays: 90 },
        });
        expect(
            classifyTouringScarcityCandidates(
                [row({ localAppearanceCount: 2 })],
                REQUEST,
            ).onlyChanceNearby,
        ).toEqual([]);
    });

    it("enforces canonical identity, eligibility, structured reasons, and deterministic show deduplication", () => {
        const eligible = row();
        const aliasOfSameCanonical = row({
            canonicalComedianUuid: "canonical-comic",
        });
        const invalidRows: TouringScarcityEvidenceRow[] = [
            row({ showId: 201, clubVisible: false }),
            row({ showId: 202, performerVisible: false }),
            row({ showId: 203, canonicalVisible: false }),
            row({ showId: 204, withinRadius: false }),
            row({ showId: 205, ticketsSoldOut: true }),
            row({ showId: 206, showName: "Sold-Out Special" }),
            row({ showId: 207, hasPurchasePath: false }),
            row({
                showId: 208,
                showDate: new Date("2026-07-01T00:00:00.000Z"),
            }),
            row({
                showId: 209,
                showDate: new Date("2026-12-01T00:00:00.000Z"),
            }),
        ];
        const selected = classifyTouringScarcityCandidates(
            [eligible, aliasOfSameCanonical, ...invalidRows],
            REQUEST,
        );

        expect(selected.justPassingThrough).toHaveLength(1);
        expect(selected.rareReturns).toHaveLength(1);
        expect(selected.onlyChanceNearby).toHaveLength(1);
        expect(selected.onlyChanceNearby[0].performer).toEqual({
            id: 10,
            uuid: "canonical-comic",
            name: "Canonical Comic",
        });
        expect(selected.onlyChanceNearby[0].reason.evidence).toEqual(
            expect.objectContaining({
                canonicalComedianId: 10,
                runStart: UPCOMING,
                runEnd: UPCOMING,
            }),
        );
    });

    it("builds one canonical, geographic, visible, actionable evidence query", () => {
        const query = buildTouringScarcityQuery({
            nearbyZips: ["94103", "94107"],
            now: NOW,
            horizonEnd: new Date("2026-10-30T12:00:00.000Z"),
        });
        const sql = query.strings.join("?");

        expect(sql).toContain(
            "COALESCE(performer.parent_comedian_id, performer.id)",
        );
        expect(sql).toContain("COUNT(DISTINCT show_id)");
        expect(sql).toContain("club.visible = true");
        expect(sql).toContain("performer.visible = true");
        expect(sql).toContain("canonical.visible = true");
        expect(sql).toContain("canonical.parent_comedian_id IS NULL");
        expect(sql).toContain('tag."restrictContent" = true');
        expect(sql).toContain("s.tickets_sold_out = false");
        expect(sql).toContain("ticket.sold_out = false");
        expect(sql).toContain("NULLIF(btrim(ticket.purchase_url), '')");
        expect(query.values).toContain("94103");
        expect(query.values).toContain("94107");
    });

    it("executes canonical scarcity evidence against relational show history", async () => {
        const pg = new PGlite();
        try {
            await pg.exec(`
                CREATE TABLE clubs (
                    id INTEGER PRIMARY KEY,
                    zip_code TEXT,
                    visible BOOLEAN NOT NULL
                );
                CREATE TABLE shows (
                    id INTEGER PRIMARY KEY,
                    club_id INTEGER NOT NULL REFERENCES clubs(id),
                    date TIMESTAMPTZ NOT NULL,
                    name TEXT,
                    tickets_sold_out BOOLEAN NOT NULL DEFAULT false
                );
                CREATE TABLE tickets (
                    id INTEGER PRIMARY KEY,
                    show_id INTEGER NOT NULL REFERENCES shows(id),
                    sold_out BOOLEAN NOT NULL DEFAULT false,
                    purchase_url TEXT
                );
                CREATE TABLE comedians (
                    id INTEGER PRIMARY KEY,
                    uuid TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    visible BOOLEAN NOT NULL DEFAULT true,
                    parent_comedian_id INTEGER REFERENCES comedians(id),
                    home_city TEXT,
                    home_state TEXT,
                    home_country TEXT,
                    home_club_id INTEGER REFERENCES clubs(id),
                    home_location_updated_at TIMESTAMPTZ
                );
                CREATE TABLE lineup_items (
                    show_id INTEGER NOT NULL REFERENCES shows(id),
                    comedian_id TEXT NOT NULL REFERENCES comedians(uuid)
                );
                CREATE TABLE tags (
                    id INTEGER PRIMARY KEY,
                    "restrictContent" BOOLEAN NOT NULL DEFAULT false
                );
                CREATE TABLE tagged_comedians (
                    comedian_id TEXT NOT NULL REFERENCES comedians(uuid),
                    tag_id INTEGER NOT NULL REFERENCES tags(id)
                );

                INSERT INTO clubs (id, zip_code, visible) VALUES
                    (1, '94103', true),
                    (2, '90001', true),
                    (3, '94107', false);
                INSERT INTO comedians
                    (id, uuid, name, visible, parent_comedian_id, home_city,
                     home_state, home_country, home_club_id,
                     home_location_updated_at)
                VALUES
                    (10, 'canonical', 'Canonical Comic', true, NULL,
                     'Los Angeles', 'CA', 'US', 2, '2026-07-01T00:00:00Z'),
                    (11, 'alias', 'Alias Comic', true, 10,
                     NULL, NULL, NULL, NULL, NULL),
                    (12, 'hidden-alias', 'Hidden Alias', false, 10,
                     NULL, NULL, NULL, NULL, NULL);

                INSERT INTO shows (id, club_id, date, name) VALUES
                    (1, 1, '2024-01-01T20:00:00Z', 'History 1'),
                    (2, 1, '2024-02-01T20:00:00Z', 'History 2'),
                    (3, 1, '2024-03-01T20:00:00Z', 'History 3'),
                    (4, 1, '2024-04-01T20:00:00Z', 'History 4'),
                    (5, 1, '2024-05-01T20:00:00Z', 'History 5'),
                    (6, 1, '2024-06-01T20:00:00Z', 'History 6'),
                    (7, 1, '2024-07-01T20:00:00Z', 'History 7'),
                    (8, 1, '2024-08-01T20:00:00Z', 'History 8'),
                    (9, 1, '2024-09-01T20:00:00Z', 'History 9'),
                    (10, 1, '2025-01-01T20:00:00Z', 'Prior Alias Date'),
                    (101, 1, '2026-08-10T20:00:00Z', 'Eligible Date'),
                    (102, 1, '2026-08-11T20:00:00Z', 'Sold Out Date'),
                    (103, 1, '2026-08-12T20:00:00Z', 'No Ticket Date'),
                    (104, 1, '2026-08-13T20:00:00Z', 'Hidden Alias Date'),
                    (105, 3, '2026-08-14T20:00:00Z', 'Hidden Club Date');
                UPDATE shows SET tickets_sold_out = true WHERE id = 102;

                INSERT INTO lineup_items (show_id, comedian_id) VALUES
                    (10, 'alias'),
                    (101, 'alias'),
                    (102, 'alias'),
                    (103, 'alias'),
                    (104, 'hidden-alias'),
                    (105, 'alias');
                INSERT INTO tickets (id, show_id, sold_out, purchase_url) VALUES
                    (1, 101, false, 'https://tickets.example.com/101'),
                    (2, 102, true, 'https://tickets.example.com/102'),
                    (3, 103, false, '   '),
                    (4, 104, false, 'https://tickets.example.com/104'),
                    (5, 105, false, 'https://tickets.example.com/105');
            `);

            const query = buildTouringScarcityQuery({
                nearbyZips: ["94103", "94107"],
                now: NOW,
                horizonEnd: new Date("2026-10-30T12:00:00.000Z"),
            });
            const converted = toPgliteQuery(query as SqlLike);
            const result = await pg.query<{
                show_id: number;
                canonical_comedian_id: number;
                canonical_comedian_uuid: string;
                local_appearance_count: number;
                prior_local_appearance_count: number;
                history_coverage_show_count: number;
                home_zip_code: string;
            }>(converted.text, converted.values);

            expect(result.rows).toEqual([
                expect.objectContaining({
                    show_id: 101,
                    canonical_comedian_id: 10,
                    canonical_comedian_uuid: "canonical",
                    local_appearance_count: 1,
                    prior_local_appearance_count: 1,
                    history_coverage_show_count: 10,
                    home_zip_code: "90001",
                }),
            ]);
        } finally {
            await pg.close();
        }
    });

    it("hydrates selected evidence through the shared public home-show mapper", async () => {
        mockQueryRaw.mockResolvedValue([rawRow()] as never);
        mockFindShowsForHome.mockResolvedValue([show()]);

        const result = await getTouringScarcityRails({
            zipCode: "94103",
            radiusMiles: 25,
            now: NOW,
        });

        expect(mockFindShowsForHome).toHaveBeenCalledWith(
            { id: { in: [101] }, club: { visible: true } },
            [{ date: "asc" }, { id: "asc" }],
            1,
            { zipCode: "94103" },
        );
        expect(result.justPassingThrough.items[0]).toMatchObject({
            show: { id: 101 },
            performer: { id: 10, uuid: "canonical-comic" },
            reason: { kind: "just_passing_through" },
        });
        expect(result.rareReturns.items[0].show.id).toBe(101);
        expect(result.onlyChanceNearby.items[0].show.id).toBe(101);
    });

    it("returns empty providers for invalid ZIPs without querying", async () => {
        const result = await getTouringScarcityRails({ zipCode: "bad" });
        expect(mockQueryRaw).not.toHaveBeenCalled();
        expect(result.justPassingThrough.items).toEqual([]);
        expect(result.rareReturns.items).toEqual([]);
        expect(result.onlyChanceNearby.items).toEqual([]);
    });
});
