import { describe, it, expect, vi, beforeEach } from "vitest";

const { mockFindMany } = vi.hoisted(() => ({
    mockFindMany: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: { show: { findMany: mockFindMany } },
}));

import { findShowDensity } from "./findShowDensity";

function makeHelper() {
    return {
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
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    mockFindMany.mockResolvedValue([]);
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
});
