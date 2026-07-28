import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/db", () => ({
    db: {
        savedShow: {
            count: vi.fn(),
            findMany: vi.fn(),
        },
    },
}));
vi.mock("@/lib/data/show/showSelect", () => ({
    PUBLIC_SHOW_SELECT: { id: true, name: true },
    mapShowRowToDTO: vi.fn((show: { id: number; name: string }) => ({
        id: show.id,
        name: show.name,
        mapped: true,
    })),
}));
vi.mock("@/lib/rateLimit", () => ({
    applyPublicReadRateLimit: vi.fn(() =>
        Promise.resolve({
            allowed: true,
            limit: 60,
            remaining: 59,
            resetAt: 0,
        }),
    ),
    rateLimitHeaders: vi.fn(() => ({ "X-RateLimit-Remaining": "42" })),
}));

import { GET } from "./route";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { db } from "@/lib/db";
import {
    PUBLIC_SHOW_SELECT,
    mapShowRowToDTO,
} from "@/lib/data/show/showSelect";
import { applyPublicReadRateLimit } from "@/lib/rateLimit";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockCount = vi.mocked(db.savedShow.count);
const mockFindMany = vi.mocked(db.savedShow.findMany);
const mockMapShowRowToDTO = vi.mocked(mapShowRowToDTO);
const mockApplyPublicReadRateLimit = vi.mocked(applyPublicReadRateLimit);

function makeRequest(query = ""): NextRequest {
    return new NextRequest(`http://localhost/api/v1/saved-shows${query}`);
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("GET /api/v1/saved-shows", () => {
    it("returns a rate-limit response before resolving auth", async () => {
        const limited = NextResponse.json(
            { error: "Too Many Requests" },
            { status: 429 },
        );
        mockApplyPublicReadRateLimit.mockResolvedValueOnce(limited);

        const response = await GET(makeRequest());

        expect(response).toBe(limited);
        expect(mockResolveAuth).not.toHaveBeenCalled();
    });

    it("returns 401 without authentication", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const response = await GET(makeRequest());

        expect(response.status).toBe(401);
        expect(await response.json()).toEqual({
            error: "Authentication required",
        });
    });

    it("returns 422 when the authenticated user has no profile", async () => {
        mockResolveAuth.mockResolvedValue(PROFILE_MISSING);

        const response = await GET(makeRequest());

        expect(response.status).toBe(422);
        expect((await response.json()).error).toMatch(/profile not found/i);
    });

    it("returns only the profile's upcoming saved shows in ascending order", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockCount.mockResolvedValue(45);
        mockFindMany.mockResolvedValue([
            { show: { id: 12, name: "Saved show" } },
        ] as never);

        const response = await GET(makeRequest("?page=2&size=20"));
        const body = await response.json();

        expect(response.status).toBe(200);
        expect(response.headers.get("Cache-Control")).toBe("private, no-store");
        expect(response.headers.get("X-RateLimit-Remaining")).toBe("42");
        expect(body).toEqual({
            data: [{ id: 12, name: "Saved show", mapped: true }],
            total: 45,
            page: 2,
            size: 20,
            totalPages: 3,
        });

        const where = mockCount.mock.calls[0]![0]!.where as {
            profileId: string;
            show: { date: { gte: Date }; club: { visible: boolean } };
        };
        expect(where.profileId).toBe("profile-1");
        expect(where.show.club).toEqual({ visible: true });
        expect(where.show.date.gte).toBeInstanceOf(Date);
        expect(mockFindMany).toHaveBeenCalledWith({
            where,
            select: { show: { select: PUBLIC_SHOW_SELECT } },
            orderBy: [{ show: { date: "asc" } }, { showId: "asc" }],
            take: 20,
            skip: 20,
        });
        expect(mockMapShowRowToDTO).toHaveBeenCalledWith(
            { id: 12, name: "Saved show" },
            {
                imageSource: "lineup",
                room: "coalesce",
                distanceWhenNoZip: "undefined",
            },
        );
    });

    it("returns past saved shows in descending order", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-2",
            userId: "user-2",
        });
        mockCount.mockResolvedValue(1);
        mockFindMany.mockResolvedValue([] as never);

        await GET(makeRequest("?period=past"));

        const query = mockFindMany.mock.calls[0]![0]!;
        const where = query.where as {
            profileId: string;
            show: { date: { lt: Date }; club: { visible: boolean } };
        };
        expect(where).toEqual({
            profileId: "profile-2",
            show: {
                date: { lt: expect.any(Date) },
                club: { visible: true },
            },
        });
        expect(query.orderBy).toEqual([
            { show: { date: "desc" } },
            { showId: "desc" },
        ]);
    });

    it("rejects an unknown period", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });

        const response = await GET(makeRequest("?period=all"));

        expect(response.status).toBe(400);
        expect(mockCount).not.toHaveBeenCalled();
        expect(mockFindMany).not.toHaveBeenCalled();
    });

    it("clamps size and falls back from invalid positive integers", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockCount.mockResolvedValue(0);
        mockFindMany.mockResolvedValue([] as never);

        const response = await GET(makeRequest("?page=-1&size=9999"));
        const body = await response.json();

        expect(body.page).toBe(1);
        expect(body.size).toBe(50);
        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({ take: 50, skip: 0 }),
        );
    });
});
