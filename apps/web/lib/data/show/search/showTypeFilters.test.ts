import { describe, expect, it, vi, beforeEach } from "vitest";
import {
    FREE_FILTER_SLUG,
    QueryHelper,
} from "@/objects/class/query/QueryHelper";

const { mockCount, mockFindMany } = vi.hoisted(() => ({
    mockCount: vi.fn(),
    mockFindMany: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: { show: { count: mockCount, findMany: mockFindMany } },
}));
vi.mock("@/util/imageUtil", () => ({
    buildClubImageUrl: vi.fn((name: string) => `/${name}.png`),
}));
vi.mock("@/util/comedian/comedianUtil", () => ({
    filterAndMapLineupItems: vi.fn(() => []),
}));
vi.mock("@/util/ticket/ticketUtil", () => ({
    mapTickets: vi.fn((tickets: object[]) => tickets),
}));

import { findShowsWithCount } from "./findShowsWithCount";

beforeEach(() => {
    vi.clearAllMocks();
    mockCount.mockResolvedValue(0);
    mockFindMany.mockResolvedValue([]);
});

describe("show type filters", () => {
    it("maps known show type filter slugs to shows.show_type", () => {
        const helper = new QueryHelper({
            params: { filters: "standup,improv" },
            timezone: "America/New_York",
        });

        expect(helper.getShowTypeClause()).toEqual({
            showType: { in: ["standup", "improv"] },
        });
    });

    it("keeps unknown filter slugs on the existing taggedShows path", () => {
        const helper = new QueryHelper({
            params: { filters: `standup,weekly,${FREE_FILTER_SLUG}` },
            timezone: "America/New_York",
        });

        expect(helper.getShowTagsClause()).toEqual({
            AND: [
                {
                    taggedShows: {
                        some: {
                            tag: {
                                slug: { in: ["weekly"] },
                                type: "show",
                            },
                        },
                    },
                },
            ],
        });
    });

    it("wires show type filters into show search count and page queries", async () => {
        const helper = new QueryHelper({
            params: { filters: "standup" },
            timezone: "America/New_York",
        });

        await findShowsWithCount(helper);

        expect(mockCount).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    showType: { in: ["standup"] },
                }),
            }),
        );
        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    showType: { in: ["standup"] },
                }),
            }),
        );
    });
});
