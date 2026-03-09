import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/db", () => ({
    db: {
        comedian: { findUnique: vi.fn() },
        favoriteComedian: { upsert: vi.fn() },
    },
}));

import { POST } from "./route";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { db } from "@/lib/db";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockFindUnique = vi.mocked(db.comedian.findUnique);
const mockUpsert = vi.mocked(db.favoriteComedian.upsert);

function makeRequest(
    body: unknown = { comedianId: "comedian-uuid-1" },
): NextRequest {
    return new NextRequest("http://localhost/api/v1/favorites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("POST /api/v1/favorites", () => {
    it("returns 422 when resolveAuth returns PROFILE_MISSING", async () => {
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING");

        const res = await POST(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(422);
        expect(body.error).toMatch(/profile not found/i);
    });

    it("returns 401 when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const res = await POST(makeRequest());

        expect(res.status).toBe(401);
    });

    it("returns 200 with isFavorited:true on success", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindUnique.mockResolvedValue({ uuid: "comedian-uuid-1" } as any);
        mockUpsert.mockResolvedValue({} as any);

        const res = await POST(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({ data: { isFavorited: true } });
    });
});
