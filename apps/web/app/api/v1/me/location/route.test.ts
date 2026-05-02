import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));

vi.mock("@/lib/rateLimit", () => ({
    checkRateLimit: vi.fn(() => ({
        allowed: true,
        limit: 100,
        remaining: 99,
        resetAt: 0,
    })),
    getClientIp: vi.fn(() => "127.0.0.1"),
    RATE_LIMITS: { authenticated: {}, authToken: {} },
    rateLimitResponse: vi.fn(() => new Response(null, { status: 429 }) as any),
}));

vi.mock("@/lib/db", () => ({
    db: {
        userProfile: {
            update: vi.fn(),
        },
    },
}));

import { PATCH } from "./route";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { db } from "@/lib/db";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockUpdateProfile = vi.mocked(db.userProfile.update);

function makeRequest(body: unknown): NextRequest {
    return new NextRequest("http://localhost/api/v1/me/location", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("PATCH /api/v1/me/location", () => {
    it("returns 401 when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const res = await PATCH(
            makeRequest({ zip_code: "94108", nearby_distance_miles: 25 }),
        );

        expect(res.status).toBe(401);
        expect(mockUpdateProfile).not.toHaveBeenCalled();
    });

    it("returns 422 when authenticated user has no UserProfile row", async () => {
        mockResolveAuth.mockResolvedValue(PROFILE_MISSING);

        const res = await PATCH(
            makeRequest({ zip_code: "94108", nearby_distance_miles: 25 }),
        );

        expect(res.status).toBe(422);
        expect(await res.json()).toEqual({ error: "profile_missing" });
        expect(mockUpdateProfile).not.toHaveBeenCalled();
    });

    it("updates the authenticated user's profile location", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-123",
            profileId: "profile-123",
        });
        mockUpdateProfile.mockResolvedValue({
            zipCode: "94108",
            nearbyDistanceMiles: 25,
        } as any);

        const res = await PATCH(
            makeRequest({ zip_code: "94108", nearby_distance_miles: 25 }),
        );

        expect(res.status).toBe(200);
        expect(mockUpdateProfile).toHaveBeenCalledWith({
            where: { userid: "user-123" },
            data: {
                zipCode: "94108",
                nearbyDistanceMiles: 25,
            },
            select: {
                zipCode: true,
                nearbyDistanceMiles: true,
            },
        });
        expect(await res.json()).toEqual({
            data: {
                zip_code: "94108",
                nearby_distance_miles: 25,
            },
        });
    });

    it("clears the authenticated user's profile location", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-123",
            profileId: "profile-123",
        });
        mockUpdateProfile.mockResolvedValue({
            zipCode: null,
            nearbyDistanceMiles: null,
        } as any);

        const res = await PATCH(
            makeRequest({ zip_code: null, nearby_distance_miles: null }),
        );

        expect(res.status).toBe(200);
        expect(mockUpdateProfile).toHaveBeenCalledWith({
            where: { userid: "user-123" },
            data: {
                zipCode: null,
                nearbyDistanceMiles: null,
            },
            select: {
                zipCode: true,
                nearbyDistanceMiles: true,
            },
        });
    });
});
