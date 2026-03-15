import { describe, it, expect, vi, beforeEach } from "vitest";
import { toggleFavorite } from "./toggleFavorite";

vi.mock("@/lib/db", () => ({
    db: {
        favoriteComedian: {
            upsert: vi.fn(),
            deleteMany: vi.fn(),
        },
    },
}));

import { db } from "@/lib/db";

const mockUpsert = db.favoriteComedian.upsert as ReturnType<typeof vi.fn>;
const mockDeleteMany = db.favoriteComedian.deleteMany as ReturnType<
    typeof vi.fn
>;

const COMEDIAN_UUID = "comedian-uuid-1";
const USER_ID = "user-id-1";

beforeEach(() => {
    vi.clearAllMocks();
    mockUpsert.mockResolvedValue({});
    mockDeleteMany.mockResolvedValue({ count: 1 });
});

describe("toggleFavorite", () => {
    describe("adding a favorite (setFavorite=true)", () => {
        it("calls upsert with the correct composite key", async () => {
            await toggleFavorite(COMEDIAN_UUID, USER_ID, true);

            expect(mockUpsert).toHaveBeenCalledOnce();
            expect(mockUpsert).toHaveBeenCalledWith({
                where: {
                    profileId_comedianId: {
                        profileId: USER_ID,
                        comedianId: COMEDIAN_UUID,
                    },
                },
                create: { profileId: USER_ID, comedianId: COMEDIAN_UUID },
                update: {},
            });
        });

        it("returns true", async () => {
            const result = await toggleFavorite(COMEDIAN_UUID, USER_ID, true);
            expect(result).toBe(true);
        });

        it("is idempotent — calling twice does not throw", async () => {
            await expect(
                toggleFavorite(COMEDIAN_UUID, USER_ID, true),
            ).resolves.toBe(true);
            await expect(
                toggleFavorite(COMEDIAN_UUID, USER_ID, true),
            ).resolves.toBe(true);
            expect(mockUpsert).toHaveBeenCalledTimes(2);
        });
    });

    describe("removing a favorite (setFavorite=false)", () => {
        it("calls deleteMany with the correct where clause", async () => {
            await toggleFavorite(COMEDIAN_UUID, USER_ID, false);

            expect(mockDeleteMany).toHaveBeenCalledOnce();
            expect(mockDeleteMany).toHaveBeenCalledWith({
                where: { comedianId: COMEDIAN_UUID, profileId: USER_ID },
            });
        });

        it("returns false", async () => {
            const result = await toggleFavorite(COMEDIAN_UUID, USER_ID, false);
            expect(result).toBe(false);
        });

        it("does not call upsert", async () => {
            await toggleFavorite(COMEDIAN_UUID, USER_ID, false);
            expect(mockUpsert).not.toHaveBeenCalled();
        });
    });
});
