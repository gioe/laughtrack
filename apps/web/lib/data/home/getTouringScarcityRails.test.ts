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
