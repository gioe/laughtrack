import { describe, it, expect, vi, beforeEach } from "vitest";
import { toggleFavoriteClub } from "./toggleFavoriteClub";

vi.mock("@/lib/db", () => ({
    db: {
        favoriteClub: {
            upsert: vi.fn(),
            deleteMany: vi.fn(),
        },
    },
}));

import { db } from "@/lib/db";

const mockUpsert = db.favoriteClub.upsert as ReturnType<typeof vi.fn>;
const mockDeleteMany = db.favoriteClub.deleteMany as ReturnType<typeof vi.fn>;

const CLUB_ID = 42;
const PROFILE_ID = "profile-id-1";

beforeEach(() => {
    vi.clearAllMocks();
    mockUpsert.mockResolvedValue({});
    mockDeleteMany.mockResolvedValue({ count: 1 });
});

describe("toggleFavoriteClub", () => {
    describe("adding a favorite (setFavorite=true)", () => {
        it("calls upsert with the correct composite key", async () => {
            await toggleFavoriteClub(CLUB_ID, PROFILE_ID, true);

            expect(mockUpsert).toHaveBeenCalledOnce();
            expect(mockUpsert).toHaveBeenCalledWith({
                where: {
                    profileId_clubId: {
                        profileId: PROFILE_ID,
                        clubId: CLUB_ID,
                    },
                },
                create: { profileId: PROFILE_ID, clubId: CLUB_ID },
                update: {},
            });
        });

        it("returns true", async () => {
            const result = await toggleFavoriteClub(CLUB_ID, PROFILE_ID, true);
            expect(result).toBe(true);
        });

        it("is idempotent — calling twice does not throw", async () => {
            await expect(
                toggleFavoriteClub(CLUB_ID, PROFILE_ID, true),
            ).resolves.toBe(true);
            await expect(
                toggleFavoriteClub(CLUB_ID, PROFILE_ID, true),
            ).resolves.toBe(true);
            expect(mockUpsert).toHaveBeenCalledTimes(2);
        });
    });

    describe("removing a favorite (setFavorite=false)", () => {
        it("calls deleteMany with the correct where clause", async () => {
            await toggleFavoriteClub(CLUB_ID, PROFILE_ID, false);

            expect(mockDeleteMany).toHaveBeenCalledOnce();
            expect(mockDeleteMany).toHaveBeenCalledWith({
                where: { clubId: CLUB_ID, profileId: PROFILE_ID },
            });
        });

        it("returns false", async () => {
            const result = await toggleFavoriteClub(
                CLUB_ID,
                PROFILE_ID,
                false,
            );
            expect(result).toBe(false);
        });

        it("does not call upsert", async () => {
            await toggleFavoriteClub(CLUB_ID, PROFILE_ID, false);
            expect(mockUpsert).not.toHaveBeenCalled();
        });

        it("is idempotent when no row exists (deleteMany count=0)", async () => {
            mockDeleteMany.mockResolvedValueOnce({ count: 0 });
            await expect(
                toggleFavoriteClub(CLUB_ID, PROFILE_ID, false),
            ).resolves.toBe(false);
        });
    });

    describe("error propagation", () => {
        it("propagates upsert rejection to the caller", async () => {
            const dbError = new Error("DB connection lost");
            mockUpsert.mockRejectedValue(dbError);

            await expect(
                toggleFavoriteClub(CLUB_ID, PROFILE_ID, true),
            ).rejects.toThrow("DB connection lost");
        });

        it("propagates deleteMany rejection to the caller", async () => {
            const dbError = new Error("DB connection lost");
            mockDeleteMany.mockRejectedValue(dbError);

            await expect(
                toggleFavoriteClub(CLUB_ID, PROFILE_ID, false),
            ).rejects.toThrow("DB connection lost");
        });
    });
});
