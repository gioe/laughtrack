import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        userProfile: {
            findFirst: vi.fn(),
        },
        $transaction: vi.fn(),
    },
}));

vi.mock("next/cache", () => ({
    revalidateTag: vi.fn(),
}));

import { POST } from "./route";
import { auth } from "@/auth";
import { db } from "@/lib/db";
import { revalidateTag } from "next/cache";

const mockAuth = vi.mocked(auth);
const mockTransaction = vi.mocked(db.$transaction);
const mockFindUserProfile = vi.mocked(db.userProfile.findFirst);
const mockRevalidateTag = vi.mocked(revalidateTag);

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

function makeRequest(body: unknown) {
    return new NextRequest("http://localhost/api/admin/clubs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

function clubRow(overrides: Record<string, unknown> = {}) {
    return {
        id: 42,
        name: "New Club",
        address: "123 Main St",
        website: "https://newclub.example.com",
        city: null,
        state: null,
        visible: true,
        status: "active",
        clubType: "club",
        closedAt: null,
        totalShows: 0,
        chain: null,
        scrapingSources: [],
        shows: [],
        _count: { shows: 0 },
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    mockFindUserProfile.mockResolvedValue({
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    } as never);
});

describe("POST /api/admin/clubs", () => {
    it("requires admin access", async () => {
        mockAuth.mockResolvedValue(null as never);

        const res = await POST(
            makeRequest({
                name: "New Club",
                address: "123 Main St",
                website: "https://newclub.example.com",
            }),
        );

        expect(res.status).toBe(401);
    });

    it("creates a club from required fields and writes an audit entry", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const auditCreate = vi.fn();
        const create = vi.fn().mockResolvedValue(clubRow());
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                club: { create },
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await POST(
            makeRequest({
                name: " New   Club ",
                address: " 123 Main St ",
                website: " https://newclub.example.com ",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(201);
        expect(create).toHaveBeenCalledWith({
            data: {
                name: "New Club",
                address: "123 Main St",
                website: "https://newclub.example.com",
            },
            select: expect.any(Object),
        });
        expect(body.club.name).toBe("New Club");
        expect(auditCreate).toHaveBeenCalledWith(
            expect.objectContaining({
                data: expect.objectContaining({
                    action: "club.create",
                    entityType: "club",
                    entityId: "42",
                }),
            }),
        );
        expect(mockRevalidateTag).toHaveBeenCalledWith("club-detail-data");
        expect(mockRevalidateTag).toHaveBeenCalledWith("New Club");
    });

    it("requires all mandatory club fields", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const res = await POST(
            makeRequest({
                name: "New Club",
                website: "https://newclub.example.com",
            }),
        );

        expect(res.status).toBe(400);
        expect(mockTransaction).not.toHaveBeenCalled();
    });
});
