import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/db", () => ({
    db: {
        favoriteComedian: { delete: vi.fn() },
    },
}));
vi.mock("@prisma/client", () => ({
    Prisma: {
        PrismaClientKnownRequestError: class PrismaClientKnownRequestError extends Error {
            code: string;
            constructor(message: string, { code }: { code: string }) {
                super(message);
                this.code = code;
            }
        },
    },
}));

import { DELETE } from "./route";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { db } from "@/lib/db";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockDelete = vi.mocked(db.favoriteComedian.delete);

function makeRequest(
    comedianId = "comedian-uuid-1",
): [NextRequest, { params: Promise<{ comedianId: string }> }] {
    const req = new NextRequest(
        `http://localhost/api/v1/favorites/${comedianId}`,
        { method: "DELETE" },
    );
    return [req, { params: Promise.resolve({ comedianId }) }];
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("DELETE /api/v1/favorites/[comedianId]", () => {
    it("returns 422 when resolveAuth returns PROFILE_MISSING", async () => {
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING");

        const [req, ctx] = makeRequest();
        const res = await DELETE(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(422);
        expect(body.error).toMatch(/profile not found/i);
    });

    it("returns 401 when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const [req, ctx] = makeRequest();
        const res = await DELETE(req, ctx);

        expect(res.status).toBe(401);
    });

    it("returns 200 with isFavorited:false on success", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockDelete.mockResolvedValue({} as any);

        const [req, ctx] = makeRequest();
        const res = await DELETE(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({ data: { isFavorited: false } });
    });
});
