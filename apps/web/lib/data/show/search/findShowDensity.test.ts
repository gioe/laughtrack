import { describe, it, expect, vi, beforeEach } from "vitest";

const { mockFindMany, mockResolveIdentity } = vi.hoisted(() => ({
    mockFindMany: vi.fn(),
    mockResolveIdentity: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: { show: { findMany: mockFindMany } },
}));
vi.mock("@/lib/data/comedian/detail/resolveCanonicalComedianIdentity", () => ({
    resolveCanonicalComedianIdentityByName: mockResolveIdentity,
}));

import { findShowDensity } from "./findShowDensity";

function makeHelper(comedian?: string) {
    return {
        params: {
            clubId: undefined as string | undefined,
            comedian,
        },
        timezone: "America/New_York",
        getDateClause: vi.fn(() => ({
            date: {
                gte: "2026-06-01T04:00:00.000Z",
                lte: "2026-06-04T03:59:59.999Z",
            },
        })),
        getZipCodeClause: vi.fn(() => ({
            zipCode: { in: ["10001", "10002"] },
        })),
        getClubNameClause: vi.fn(() => ({})),
        getLineupItemClause: vi.fn((memberUuids?: string[]) => ({
            lineupItems: comedian
                ? { some: { comedianId: { in: memberUuids ?? [] } } }
                : {},
        })),
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    mockFindMany.mockResolvedValue([]);
    mockResolveIdentity.mockResolvedValue({
        rootId: 1,
        rootUuid: "canonical-uuid",
        memberUuids: ["canonical-uuid", "alias-uuid"],
    });
});

describe("findShowDensity", () => {
    it("returns integer counts keyed by ISO date in the request timezone", async () => {
        mockFindMany.mockResolvedValue([
            { date: new Date("2026-06-01T23:30:00.000Z") },
            { date: new Date("2026-06-02T01:00:00.000Z") },
            { date: new Date("2026-06-03T04:30:00.000Z") },
        ]);

        const result = await findShowDensity(makeHelper() as never);

        expect(result).toEqual({
            "2026-06-01": 2,
            "2026-06-03": 1,
        });
    });

    it("filters to visible clubs and applies the helper zip clause when present", async () => {
        const helper = makeHelper();

        await findShowDensity(helper as never);

        expect(mockFindMany).toHaveBeenCalledWith({
            where: {
                date: {
                    gte: "2026-06-01T04:00:00.000Z",
                    lte: "2026-06-04T03:59:59.999Z",
                },
                club: {
                    visible: true,
                    zipCode: { in: ["10001", "10002"] },
                },
                lineupItems: {},
            },
            select: { date: true },
        });
    });

    it("omits the zip filter when no zip clause is present", async () => {
        const helper = {
            ...makeHelper(),
            getZipCodeClause: vi.fn(() => ({})),
        };

        await findShowDensity(helper as never);

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    club: { visible: true },
                }),
            }),
        );
    });

    it("applies the helper lineup clause when a comedian filter is set", async () => {
        const helper = {
            ...makeHelper("Akaash Singh"),
            getZipCodeClause: vi.fn(() => ({})),
            getLineupItemClause: vi.fn((memberUuids?: string[]) => ({
                lineupItems: {
                    some: {
                        comedianId: { in: memberUuids ?? [] },
                    },
                },
            })),
        };

        await findShowDensity(helper as never);

        expect(helper.getLineupItemClause).toHaveBeenCalledTimes(1);
        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    lineupItems: {
                        some: {
                            comedianId: {
                                in: ["canonical-uuid", "alias-uuid"],
                            },
                        },
                    },
                }),
            }),
        );
        expect(mockResolveIdentity).toHaveBeenCalledWith("Akaash Singh");
    });

    it("applies the helper club-name clause when a club filter is set", async () => {
        const helper = {
            ...makeHelper(),
            getZipCodeClause: vi.fn(() => ({})),
            getClubNameClause: vi.fn(() => ({
                name: { contains: "Comedy Cellar" },
            })),
        };

        await findShowDensity(helper as never);

        expect(helper.getClubNameClause).toHaveBeenCalledTimes(1);
        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    club: {
                        visible: true,
                        name: { contains: "Comedy Cellar" },
                    },
                }),
            }),
        );
    });

    it("applies an exact club id without changing club-name matching", async () => {
        const helper = {
            ...makeHelper(),
            params: { clubId: "5" },
            getZipCodeClause: vi.fn(() => ({})),
            getClubNameClause: vi.fn(() => ({
                name: { contains: "The Stand" },
            })),
        };

        await findShowDensity(helper as never);

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    club: {
                        visible: true,
                        id: 5,
                        name: { contains: "The Stand" },
                    },
                }),
            }),
        );
    });

    it("composes zip + comedian clauses together in a single where", async () => {
        const helper = {
            ...makeHelper("Akaash Singh"),
            getLineupItemClause: vi.fn((memberUuids?: string[]) => ({
                lineupItems: {
                    some: {
                        comedianId: { in: memberUuids ?? [] },
                    },
                },
            })),
        };

        await findShowDensity(helper as never);

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    club: {
                        visible: true,
                        zipCode: { in: ["10001", "10002"] },
                    },
                    lineupItems: {
                        some: expect.objectContaining({
                            comedianId: {
                                in: ["canonical-uuid", "alias-uuid"],
                            },
                        }),
                    },
                }),
            }),
        );
    });
});
