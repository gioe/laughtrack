import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { club: { findMany: vi.fn() } },
}));
vi.mock("@/util/imageUtil", () => ({
    buildClubImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.jpg`,
    ),
}));
vi.mock("zipcodes", () => ({
    default: {
        radius: vi.fn(() => ["10801", "10802"]),
    },
}));

import { getClubsByZip } from "./getClubsByZip";
import { db } from "@/lib/db";

const mockFindMany = vi.mocked(db.club.findMany);

function makeClubRow(
    overrides: Partial<{
        id: number;
        address: string;
        zipCode: string | null;
        name: string;
        hasImage: boolean;
        shows: { lineupItems: { comedianId: number }[] }[];
    }> = {},
) {
    return {
        id: 1,
        address: "123 Main St",
        zipCode: "10801",
        name: "Laughs Club",
        hasImage: true,
        shows: [],
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("getClubsByZip", () => {
    it("returns no clubs for an invalid ZIP without querying", async () => {
        const result = await getClubsByZip("not-a-zip", 25);

        expect(result).toEqual([]);
        expect(mockFindMany).not.toHaveBeenCalled();
    });

    it("scopes clubs to the radius-resolved nearby ZIP codes", async () => {
        mockFindMany.mockResolvedValue([] as never);

        await getClubsByZip("10801", 25);

        const call = mockFindMany.mock.calls[0][0];
        expect(call?.where).toMatchObject({
            status: "active",
            zipCode: { in: ["10801", "10802"] },
            shows: { some: { date: { gt: expect.any(Date) } } },
        });
    });

    it("requires venue images when requireImage is set", async () => {
        mockFindMany.mockResolvedValue([] as never);

        await getClubsByZip("10801", 25, 8, { requireImage: true });

        const call = mockFindMany.mock.calls[0][0];
        expect(call?.where).toMatchObject({ hasImage: true });
    });

    it("omits the hasImage filter by default", async () => {
        mockFindMany.mockResolvedValue([] as never);

        await getClubsByZip("10801", 25);

        const call = mockFindMany.mock.calls[0][0];
        expect(call?.where).not.toHaveProperty("hasImage");
    });

    it("maps DB rows to ClubDTOs with a deduplicated comedian count", async () => {
        mockFindMany.mockResolvedValue([
            makeClubRow({
                id: 7,
                name: "Funny Bones",
                shows: [
                    { lineupItems: [{ comedianId: 1 }, { comedianId: 2 }] },
                    { lineupItems: [{ comedianId: 2 }, { comedianId: 3 }] },
                ],
            }),
        ] as never);

        const result = await getClubsByZip("10801", 25);

        expect(result).toHaveLength(1);
        expect(result[0]).toMatchObject({
            id: 7,
            name: "Funny Bones",
            zipCode: "10801",
            imageUrl: "https://cdn.example.com/Funny Bones.jpg",
            activeComedianCount: 3,
        });
    });

    it("clamps the limit to the 1–100 range", async () => {
        mockFindMany.mockResolvedValue([] as never);

        await getClubsByZip("10801", 25, 500);
        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({ take: 100 }),
        );
    });
});
