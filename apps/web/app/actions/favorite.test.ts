import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));
vi.mock("@/lib/data/favorites/toggleFavorite", () => ({
    toggleFavorite: vi.fn(),
}));

import { favorite } from "./favorite";
import { auth } from "@/auth";
import { toggleFavorite } from "@/lib/data/favorites/toggleFavorite";

const mockAuth = vi.mocked(auth);
const mockToggleFavorite = vi.mocked(toggleFavorite);

const COMEDIAN_ID = "comedian-uuid-1";
const USER_ID = "user-123";
const PROFILE_ID = "profile-456";

const FULL_SESSION = {
    user: { id: USER_ID },
    profile: { id: PROFILE_ID },
};

beforeEach(() => {
    vi.clearAllMocks();
});

describe("favorite server action", () => {
    describe("Zod validation", () => {
        it("returns validation error when comedianId is empty", async () => {
            const result = await favorite(true, "");

            expect(result).toEqual({ error: "comedianId is required" });
            expect(mockAuth).not.toHaveBeenCalled();
            expect(mockToggleFavorite).not.toHaveBeenCalled();
        });
    });

    describe("auth branches", () => {
        it("returns undefined when session is missing", async () => {
            mockAuth.mockResolvedValue(null as never);

            const result = await favorite(true, COMEDIAN_ID);

            expect(result).toBeUndefined();
            expect(mockToggleFavorite).not.toHaveBeenCalled();
        });

        it("returns undefined when session has no user", async () => {
            mockAuth.mockResolvedValue({ user: null } as never);

            const result = await favorite(true, COMEDIAN_ID);

            expect(result).toBeUndefined();
            expect(mockToggleFavorite).not.toHaveBeenCalled();
        });

        it("returns undefined when session user has no id", async () => {
            mockAuth.mockResolvedValue({ user: {} } as never);

            const result = await favorite(true, COMEDIAN_ID);

            expect(result).toBeUndefined();
            expect(mockToggleFavorite).not.toHaveBeenCalled();
        });

        it("returns profile error when session.profile is missing", async () => {
            mockAuth.mockResolvedValue({
                user: { id: USER_ID },
            } as never);

            const result = await favorite(true, COMEDIAN_ID);

            expect(result).toEqual({
                error: "User profile not found. Please sign out and sign in again.",
            });
            expect(mockToggleFavorite).not.toHaveBeenCalled();
        });

        it("returns profile error when session.profile.id is missing", async () => {
            mockAuth.mockResolvedValue({
                user: { id: USER_ID },
                profile: {},
            } as never);

            const result = await favorite(true, COMEDIAN_ID);

            expect(result).toEqual({
                error: "User profile not found. Please sign out and sign in again.",
            });
            expect(mockToggleFavorite).not.toHaveBeenCalled();
        });
    });

    describe("happy path", () => {
        it("delegates to toggleFavorite with parsed args when setting favorite", async () => {
            mockAuth.mockResolvedValue(FULL_SESSION as never);
            mockToggleFavorite.mockResolvedValue(true);

            const result = await favorite(true, COMEDIAN_ID);

            expect(result).toBe(true);
            expect(mockToggleFavorite).toHaveBeenCalledExactlyOnceWith(
                COMEDIAN_ID,
                PROFILE_ID,
                true,
            );
        });

        it("delegates to toggleFavorite with parsed args when unsetting favorite", async () => {
            mockAuth.mockResolvedValue(FULL_SESSION as never);
            mockToggleFavorite.mockResolvedValue(false);

            const result = await favorite(false, COMEDIAN_ID);

            expect(result).toBe(false);
            expect(mockToggleFavorite).toHaveBeenCalledExactlyOnceWith(
                COMEDIAN_ID,
                PROFILE_ID,
                false,
            );
        });

        it("swallows toggleFavorite errors and returns undefined", async () => {
            mockAuth.mockResolvedValue(FULL_SESSION as never);
            mockToggleFavorite.mockRejectedValue(new Error("db down"));
            const consoleSpy = vi
                .spyOn(console, "error")
                .mockImplementation(() => {});

            const result = await favorite(true, COMEDIAN_ID);

            expect(result).toBeUndefined();
            expect(consoleSpy).toHaveBeenCalled();
            consoleSpy.mockRestore();
        });
    });
});
