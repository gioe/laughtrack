import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryHelper } from "@/objects/class/query/QueryHelper";

const { mockCount, mockFindMany, mockComputeDistanceMiles } = vi.hoisted(
    () => ({
        mockCount: vi.fn(),
        mockFindMany: vi.fn(),
        mockComputeDistanceMiles: vi.fn(),
    }),
);

vi.mock("@/lib/db", () => ({
    db: { club: { count: mockCount, findMany: mockFindMany } },
}));
vi.mock("@/util/imageUtil", () => ({
    buildClubImageUrl: vi.fn((name: string) => `/${name}.png`),
}));
vi.mock("@/util/distanceUtil", () => ({
    computeDistanceMiles: mockComputeDistanceMiles,
}));

import { findClubsWithCount } from "./findClubsWithCount";

const clubRow = {
    id: 1,
    name: "Nearby Comedy Club",
    address: "1 Main St",
    city: "New York",
    state: "NY",
    website: "https://example.com",
    zipCode: "10002",
    hasImage: false,
    clubType: "club",
    chainId: null,
    chain: null,
    discoveryProfile: null,
    _count: { shows: 3 },
};

function makeHelper(
    params: ConstructorParameters<typeof QueryHelper>[0]["params"],
) {
    return new QueryHelper({
        params: { includeEmpty: "true", chain: "any-chain", ...params },
        timezone: "America/New_York",
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockCount.mockResolvedValue(1);
    mockFindMany.mockResolvedValue([clubRow]);
    mockComputeDistanceMiles.mockReturnValue(4.2);
});

describe("club search location filtering", () => {
    it("applies the resolved radius to active visible count and page queries", async () => {
        const result = await findClubsWithCount(
            makeHelper({ zip: "10001", distance: "10" }),
        );

        const countWhere = mockCount.mock.calls[0][0].where;
        const pageWhere = mockFindMany.mock.calls[0][0].where;

        for (const where of [countWhere, pageWhere]) {
            expect(where).toEqual(
                expect.objectContaining({
                    visible: true,
                    status: "active",
                    zipCode: { in: expect.arrayContaining(["10001"]) },
                }),
            );
        }
        expect(result.totalCount).toBe(1);
        expect(result.clubs[0].distanceMiles).toBe(4.2);
        expect(mockComputeDistanceMiles).toHaveBeenCalledWith("10001", "10002");
    });

    it("leaves club search nationwide when location is absent", async () => {
        await findClubsWithCount(makeHelper({}));

        expect(mockCount.mock.calls[0][0].where).not.toHaveProperty("zipCode");
        expect(mockFindMany.mock.calls[0][0].where).not.toHaveProperty(
            "zipCode",
        );
        expect(mockComputeDistanceMiles).toHaveBeenCalledWith(
            undefined,
            "10002",
        );
    });

    it("uses the same location clause when selecting a nearby chain flagship", async () => {
        const helper = new QueryHelper({
            params: {
                zip: "10001",
                distance: "10",
                includeEmpty: "true",
            },
            timezone: "America/New_York",
        });
        mockFindMany
            .mockResolvedValueOnce([
                {
                    id: 2,
                    chainId: 9,
                    name: "Nearby Chain Location",
                    _count: { shows: 5 },
                },
            ])
            .mockResolvedValueOnce([
                {
                    ...clubRow,
                    id: 2,
                    chainId: 9,
                    name: "Nearby Chain Location",
                },
            ]);

        await findClubsWithCount(helper);

        const flagshipWhere = mockFindMany.mock.calls[0][0].where;
        const countWhere = mockCount.mock.calls[0][0].where;
        const pageWhere = mockFindMany.mock.calls[1][0].where;

        for (const where of [flagshipWhere, countWhere, pageWhere]) {
            expect(where.AND[0]).toEqual(
                expect.objectContaining({
                    visible: true,
                    status: "active",
                    zipCode: { in: expect.arrayContaining(["10001"]) },
                }),
            );
        }
    });
});
