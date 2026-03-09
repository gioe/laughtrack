import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { club: { findMany: vi.fn() } },
}));
vi.mock("@/util/imageUtil", () => ({
    buildClubImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.jpg`,
    ),
}));

import { getClubs } from "./getClubs";
import { db } from "@/lib/db";

const mockFindMany = vi.mocked(db.club.findMany);

function makeClubRow(
    overrides: Partial<{
        id: number;
        address: string;
        zipCode: string | null;
        name: string;
        shows: { lineupItems: { comedianId: number }[] }[];
    }> = {},
) {
    return {
        id: 1,
        address: "123 Main St",
        zipCode: "10001",
        name: "Laughs Club",
        shows: [],
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("getClubs", () => {
    describe("ClubDTO shape", () => {
        it("maps a single DB row to a ClubDTO with all required fields", async () => {
            const row = makeClubRow({
                id: 42,
                name: "Funny Bones",
                address: "456 Elm St",
                zipCode: "90210",
            });
            mockFindMany.mockResolvedValue([row] as any);

            const result = await getClubs();

            expect(result).toHaveLength(1);
            const dto = result[0];
            expect(dto.id).toBe(42);
            expect(dto.name).toBe("Funny Bones");
            expect(dto.address).toBe("456 Elm St");
            expect(dto.zipCode).toBe("90210");
            expect(dto.imageUrl).toBe(
                "https://cdn.example.com/Funny Bones.jpg",
            );
            expect(typeof dto.active_comedian_count).toBe("number");
        });

        it("returns an empty array when the DB returns no rows", async () => {
            mockFindMany.mockResolvedValue([] as any);
            const result = await getClubs();
            expect(result).toEqual([]);
        });

        it("passes DB errors through as unhandled rejections", async () => {
            mockFindMany.mockRejectedValue(new Error("DB unavailable"));
            await expect(getClubs()).rejects.toThrow("DB unavailable");
        });
    });

    describe("active_comedian_count — unique comedians across shows", () => {
        it("counts unique comedian IDs across all shows within the 30-day window", async () => {
            const row = makeClubRow({
                shows: [
                    { lineupItems: [{ comedianId: 1 }, { comedianId: 2 }] },
                    { lineupItems: [{ comedianId: 2 }, { comedianId: 3 }] },
                ],
            });
            mockFindMany.mockResolvedValue([row] as any);

            const result = await getClubs();
            // IDs 1, 2, 3 — comedian 2 appears in two shows but is counted once
            expect(result[0].active_comedian_count).toBe(3);
        });

        it("returns 0 when a club has no shows", async () => {
            mockFindMany.mockResolvedValue([makeClubRow({ shows: [] })] as any);
            const result = await getClubs();
            expect(result[0].active_comedian_count).toBe(0);
        });

        it("returns 0 when shows have no lineup items", async () => {
            const row = makeClubRow({
                shows: [{ lineupItems: [] }, { lineupItems: [] }],
            });
            mockFindMany.mockResolvedValue([row] as any);
            const result = await getClubs();
            expect(result[0].active_comedian_count).toBe(0);
        });

        it("deduplicates the same comedian appearing in multiple shows", async () => {
            const row = makeClubRow({
                shows: [
                    { lineupItems: [{ comedianId: 5 }] },
                    { lineupItems: [{ comedianId: 5 }] },
                    { lineupItems: [{ comedianId: 5 }] },
                ],
            });
            mockFindMany.mockResolvedValue([row] as any);
            const result = await getClubs();
            expect(result[0].active_comedian_count).toBe(1);
        });

        it("computes independent counts per club", async () => {
            const rows = [
                makeClubRow({
                    id: 1,
                    name: "Club A",
                    shows: [
                        { lineupItems: [{ comedianId: 1 }, { comedianId: 2 }] },
                    ],
                }),
                makeClubRow({
                    id: 2,
                    name: "Club B",
                    shows: [{ lineupItems: [{ comedianId: 3 }] }],
                }),
            ];
            mockFindMany.mockResolvedValue(rows as any);
            const result = await getClubs();
            expect(result[0].active_comedian_count).toBe(2);
            expect(result[1].active_comedian_count).toBe(1);
        });
    });

    describe("safeLimit clamp (1–100)", () => {
        it("passes the default limit of 8 to findMany", async () => {
            mockFindMany.mockResolvedValue([] as any);
            await getClubs();
            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ take: 8, orderBy: { id: "asc" } }),
            );
        });

        it("clamps limit below 1 to 1", async () => {
            mockFindMany.mockResolvedValue([] as any);
            await getClubs(0);
            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ take: 1 }),
            );
        });

        it("clamps negative limit to 1", async () => {
            mockFindMany.mockResolvedValue([] as any);
            await getClubs(-50);
            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ take: 1 }),
            );
        });

        it("clamps limit above 100 to 100", async () => {
            mockFindMany.mockResolvedValue([] as any);
            await getClubs(500);
            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ take: 100 }),
            );
        });

        it("preserves a valid limit within 1–100", async () => {
            mockFindMany.mockResolvedValue([] as any);
            await getClubs(50);
            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ take: 50 }),
            );
        });

        it("preserves the boundary value 1", async () => {
            mockFindMany.mockResolvedValue([] as any);
            await getClubs(1);
            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ take: 1 }),
            );
        });

        it("preserves the boundary value 100", async () => {
            mockFindMany.mockResolvedValue([] as any);
            await getClubs(100);
            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ take: 100 }),
            );
        });
    });

    describe("offset (skip) parameter", () => {
        it("passes the default offset of 0 to findMany", async () => {
            mockFindMany.mockResolvedValue([] as any);
            await getClubs();
            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ skip: 0 }),
            );
        });

        it("passes a custom offset to findMany", async () => {
            mockFindMany.mockResolvedValue([] as any);
            await getClubs(8, 16);
            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ skip: 16 }),
            );
        });

        it("passes offset and clamped limit together", async () => {
            mockFindMany.mockResolvedValue([] as any);
            await getClubs(500, 10);
            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ take: 100, skip: 10 }),
            );
        });
    });
});
