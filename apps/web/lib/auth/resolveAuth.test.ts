import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const mocks = vi.hoisted(() => ({
    auth: vi.fn(),
    findUser: vi.fn(),
    verifyToken: vi.fn(),
}));

vi.mock("@/auth", () => ({
    auth: mocks.auth,
}));

vi.mock("@/lib/db", () => ({
    db: {
        user: {
            findUnique: mocks.findUser,
        },
    },
}));

vi.mock("@/util/token", () => ({
    verifyToken: mocks.verifyToken,
}));

import { auth } from "@/auth";
import { db } from "@/lib/db";
import { verifyToken } from "@/util/token";
import { PROFILE_MISSING, resolveAuth } from "./resolveAuth";

const mockAuth = vi.mocked(auth);
const mockFindUser = vi.mocked(db.user.findUnique);
const mockVerifyToken = vi.mocked(verifyToken);

function makeRequest(headers: Record<string, string> = {}): NextRequest {
    return new NextRequest("http://localhost/api/v1/me", { headers });
}

describe("resolveAuth", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("resolves Bearer tokens before falling back to NextAuth session cookies", async () => {
        mockVerifyToken.mockReturnValue({
            email: "mobile@example.com",
        } as never);
        mockFindUser.mockResolvedValue({
            id: "user-1",
            profile: { id: "profile-1", role: "admin" },
        } as never);

        const result = await resolveAuth(
            makeRequest({ authorization: "Bearer access-token" }),
        );

        expect(result).toEqual({
            profileId: "profile-1",
            userId: "user-1",
            role: "admin",
        });
        expect(mockVerifyToken).toHaveBeenCalledWith("access-token");
        expect(mockFindUser).toHaveBeenCalledWith({
            where: { email: "mobile@example.com" },
            select: {
                id: true,
                profile: { select: { id: true, role: true } },
            },
        });
        expect(mockAuth).not.toHaveBeenCalled();
    });

    it("returns null when a valid Bearer token has no matching user", async () => {
        mockVerifyToken.mockReturnValue({
            email: "missing@example.com",
        } as never);
        mockFindUser.mockResolvedValue(null);

        await expect(
            resolveAuth(makeRequest({ authorization: "Bearer access-token" })),
        ).resolves.toBeNull();
        expect(mockAuth).not.toHaveBeenCalled();
    });

    it("returns PROFILE_MISSING when Bearer auth has a user without a profile", async () => {
        mockVerifyToken.mockReturnValue({
            email: "mobile@example.com",
        } as never);
        mockFindUser.mockResolvedValue({
            id: "user-1",
            profile: null,
        } as never);

        await expect(
            resolveAuth(makeRequest({ authorization: "Bearer access-token" })),
        ).resolves.toBe(PROFILE_MISSING);
        expect(mockAuth).not.toHaveBeenCalled();
    });

    it("treats invalid Bearer tokens as anonymous and logs only the error message", async () => {
        const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
        try {
            mockVerifyToken.mockImplementation(() => {
                throw new Error("expired token");
            });

            await expect(
                resolveAuth(
                    makeRequest({ authorization: "Bearer expired-token" }),
                ),
            ).resolves.toBeNull();

            expect(mockFindUser).not.toHaveBeenCalled();
            expect(mockAuth).not.toHaveBeenCalled();
            expect(warnSpy).toHaveBeenCalledWith(
                "Bearer token auth failed:",
                "expired token",
            );
        } finally {
            warnSpy.mockRestore();
        }
    });

    it("falls back to NextAuth session cookies when Authorization is absent", async () => {
        mockAuth.mockResolvedValue({
            profile: {
                id: "profile-2",
                userid: "user-2",
                role: "user",
            },
        } as never);

        await expect(resolveAuth(makeRequest())).resolves.toEqual({
            profileId: "profile-2",
            userId: "user-2",
            role: "user",
        });
        expect(mockVerifyToken).not.toHaveBeenCalled();
        expect(mockFindUser).not.toHaveBeenCalled();
    });

    it("returns null when neither Bearer auth nor a session is present", async () => {
        mockAuth.mockResolvedValue(null as never);

        await expect(resolveAuth(makeRequest())).resolves.toBeNull();
    });

    it("returns PROFILE_MISSING when the session has no complete profile identity", async () => {
        mockAuth.mockResolvedValue({
            profile: {
                id: "profile-2",
                userid: "",
                role: "user",
            },
        } as never);

        await expect(resolveAuth(makeRequest())).resolves.toBe(PROFILE_MISSING);
    });
});
