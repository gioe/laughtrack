import { beforeEach, describe, expect, it, vi } from "vitest";
import { db } from "@/lib/db";
import { findCoBilledComediansForComedian } from "./findCoBilledComediansForComedian";

vi.mock("@/lib/db", () => ({
    db: {
        $queryRaw: vi.fn(),
        comedian: {
            findMany: vi.fn(),
        },
    },
}));

const mockQueryRaw = vi.mocked(db.$queryRaw);
const mockFindMany = vi.mocked(db.comedian.findMany);

describe("findCoBilledComediansForComedian", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("returns comedians with at least two historical co-bills in co-occurrence order", async () => {
        mockQueryRaw.mockResolvedValue([
            { uuid: "frequent-co-bill", co_bill_count: 4 },
            { uuid: "second-co-bill", co_bill_count: 2 },
        ] as never);
        mockFindMany.mockResolvedValue([
            {
                id: 20,
                uuid: "second-co-bill",
                name: "Second Comic",
                hasImage: false,
                _count: { lineupItems: 5 },
                parentComedian: null,
                taggedComedians: [],
            },
            {
                id: 10,
                uuid: "frequent-co-bill",
                name: "Frequent Comic",
                hasImage: true,
                _count: { lineupItems: 8 },
                parentComedian: null,
                taggedComedians: [],
            },
        ] as never);

        const result = await findCoBilledComediansForComedian({
            comedianId: 123,
            now: new Date("2026-05-10T12:00:00Z"),
        });

        expect(result).toEqual([
            expect.objectContaining({
                id: 10,
                uuid: "frequent-co-bill",
                name: "Frequent Comic",
                show_count: 8,
            }),
            expect.objectContaining({
                id: 20,
                uuid: "second-co-bill",
                name: "Second Comic",
                show_count: 5,
            }),
        ]);
        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: { uuid: { in: ["frequent-co-bill", "second-co-bill"] } },
            }),
        );
    });

    it("returns an empty list without a follow-up lookup when no co-bills qualify", async () => {
        mockQueryRaw.mockResolvedValue([] as never);

        const result = await findCoBilledComediansForComedian({
            comedianId: 123,
            now: new Date("2026-05-10T12:00:00Z"),
        });

        expect(result).toEqual([]);
        expect(mockFindMany).not.toHaveBeenCalled();
    });

    it("does not return the requested comedian when an alias maps back to the target", async () => {
        mockQueryRaw.mockResolvedValue([
            { uuid: "target-alias", co_bill_count: 3 },
        ] as never);
        mockFindMany.mockResolvedValue([
            {
                id: 999,
                uuid: "target-alias",
                name: "Target Alias",
                hasImage: false,
                _count: { lineupItems: 3 },
                parentComedian: {
                    id: 123,
                    uuid: "target-uuid",
                    name: "Target Comedian",
                    hasImage: true,
                    _count: { lineupItems: 20 },
                    taggedComedians: [],
                },
                taggedComedians: [],
            },
        ] as never);

        const result = await findCoBilledComediansForComedian({
            comedianId: 123,
            now: new Date("2026-05-10T12:00:00Z"),
        });

        expect(result).toEqual([]);
    });
});
