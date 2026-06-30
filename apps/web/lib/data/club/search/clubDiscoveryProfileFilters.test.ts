import { describe, expect, it, vi, beforeEach } from "vitest";
import { QueryHelper } from "@/objects/class/query/QueryHelper";

const { mockCount, mockFindMany } = vi.hoisted(() => ({
    mockCount: vi.fn(),
    mockFindMany: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: { club: { count: mockCount, findMany: mockFindMany } },
}));
vi.mock("@/util/imageUtil", () => ({
    buildClubImageUrl: vi.fn((name: string) => `/${name}.png`),
}));
vi.mock("@/util/distanceUtil", () => ({
    computeDistanceMiles: vi.fn(() => null),
}));

import { findClubsWithCount } from "./findClubsWithCount";

beforeEach(() => {
    vi.clearAllMocks();
    mockCount.mockResolvedValue(0);
    mockFindMany.mockResolvedValue([]);
});

describe("club discovery profile filters", () => {
    it("maps known programming slugs to club discovery profile fields", () => {
        const helper = new QueryHelper({
            params: { filters: "standup,mixed_programming" },
            timezone: "America/New_York",
        });

        expect(helper.getClubDiscoveryProfileFiltersClause()).toEqual({
            discoveryProfile: {
                is: {
                    OR: [
                        { primaryShowType: { in: ["standup"] } },
                        { mixedProgramming: true },
                    ],
                },
            },
        });
    });

    it("keeps non-programming filter slugs on the existing taggedClubs path", () => {
        const helper = new QueryHelper({
            params: { filters: "standup,neighborhood-favorite" },
            timezone: "America/New_York",
        });

        expect(helper.getClubFiltersClause()).toEqual({
            AND: [
                {
                    taggedClubs: {
                        some: {
                            tag: {
                                slug: { in: ["neighborhood-favorite"] },
                                type: "club",
                            },
                        },
                    },
                },
            ],
        });
    });

    it("maps festival and producer filters to normalized club type fields", () => {
        const helper = new QueryHelper({
            params: { filters: "festival,producer,neighborhood-favorite" },
            timezone: "America/New_York",
        });

        expect(helper.getClubTypeFiltersClause()).toEqual({
            clubType: { in: ["festival", "producer"] },
        });
        expect(helper.getClubFiltersClause()).toEqual({
            AND: [
                {
                    taggedClubs: {
                        some: {
                            tag: {
                                slug: { in: ["neighborhood-favorite"] },
                                type: "club",
                            },
                        },
                    },
                },
            ],
        });
    });

    it("wires discovery profile filters into club search count and page queries", async () => {
        const helper = new QueryHelper({
            params: {
                chain: "any-chain",
                filters: "improv",
                includeEmpty: "true",
            },
            timezone: "America/New_York",
        });

        await findClubsWithCount(helper);

        expect(mockCount).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    discoveryProfile: {
                        is: {
                            primaryShowType: { in: ["improv"] },
                        },
                    },
                }),
            }),
        );
        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    discoveryProfile: {
                        is: {
                            primaryShowType: { in: ["improv"] },
                        },
                    },
                }),
            }),
        );
    });
});
