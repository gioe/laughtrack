import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        $transaction: vi.fn(),
        userProfile: {
            findFirst: vi.fn(),
        },
    },
}));

vi.mock("next/cache", () => ({
    revalidateTag: vi.fn(),
}));

import { PATCH, PUT } from "./route";
import { auth } from "@/auth";
import { db } from "@/lib/db";

const mockAuth = vi.mocked(auth);
const mockTransaction = vi.mocked(db.$transaction);
const mockFindUserProfile = vi.mocked(db.userProfile.findFirst);

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

function makeRequest(body: unknown) {
    return new NextRequest("http://localhost/api/admin/comedians", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

function makeComedian(overrides: Record<string, unknown> = {}) {
    return {
        id: 2,
        uuid: "uuid-2",
        name: "Alias Comic",
        website: null,
        websiteScrapingUrl: null,
        popularity: 12,
        totalShows: 1,
        parentComedianId: null,
        parentComedian: null,
        comedianPodcasts: [],
        lineupItems: [],
        _count: { alternativeNames: 0 },
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

describe("PATCH /api/admin/comedians", () => {
    it("requires admin access", async () => {
        mockAuth.mockResolvedValue(null as never);

        const res = await PATCH(
            makeRequest({
                action: "set-parent",
                comedianId: 2,
                parentComedianId: 1,
            }),
        );

        expect(res.status).toBe(401);
    });

    it("saves a parent relationship and writes an audit entry", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const auditCreate = vi.fn();
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(makeComedian())
            .mockResolvedValueOnce(
                makeComedian({ id: 1, name: "Parent Comic" }),
            )
            .mockResolvedValueOnce({ parentComedianId: null })
            .mockResolvedValueOnce(
                makeComedian({
                    parentComedianId: 1,
                    parentComedian: { id: 1, name: "Parent Comic" },
                }),
            );
        const txQueryRaw = vi.fn().mockResolvedValueOnce([]);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PATCH(
            makeRequest({
                action: "set-parent",
                comedianId: 2,
                parentComedianId: 1,
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: { parentComedianId: 1 },
        });
        expect(body.comedian.parent).toEqual({ id: 1, name: "Parent Comic" });
        expect(auditCreate).toHaveBeenCalledWith(
            expect.objectContaining({
                data: expect.objectContaining({
                    action: "comedian.parent.update",
                    entityType: "comedian",
                    entityId: "2",
                }),
            }),
        );
    });

    it("adds the comedian name to the deny list", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const auditCreate = vi.fn();
        const findUnique = vi.fn().mockResolvedValueOnce(makeComedian());
        const txQueryRaw = vi
            .fn()
            .mockResolvedValueOnce([])
            .mockResolvedValueOnce([
                {
                    name: "Alias Comic",
                    reason: "Not a comedian",
                    added_by: "profile-1",
                    deleted_at: new Date("2026-05-19T12:00:00Z"),
                },
            ]);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique },
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PATCH(
            makeRequest({
                action: "blocklist-add",
                comedianId: 2,
                reason: "Not a comedian",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.comedian.isBlocked).toBe(true);
        expect(body.comedian.blockReason).toBe("Not a comedian");
        expect(auditCreate).toHaveBeenCalledWith(
            expect.objectContaining({
                data: expect.objectContaining({
                    action: "comedian_deny_list.create",
                    entityType: "comedian_deny_list",
                    entityId: "Alias Comic",
                }),
            }),
        );
    });

    it("removes the comedian name from the deny list", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const auditCreate = vi.fn();
        const findUnique = vi.fn().mockResolvedValueOnce(makeComedian());
        const denyListEntry = {
            name: "Alias Comic",
            reason: "Not a comedian",
            added_by: "profile-1",
            deleted_at: new Date("2026-05-19T12:00:00Z"),
        };
        const txQueryRaw = vi
            .fn()
            .mockResolvedValueOnce([denyListEntry])
            .mockResolvedValueOnce([denyListEntry]);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique },
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PATCH(
            makeRequest({
                action: "blocklist-remove",
                comedianId: 2,
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.comedian.isBlocked).toBe(false);
        expect(body.comedian.blockReason).toBeNull();
        expect(auditCreate).toHaveBeenCalledWith(
            expect.objectContaining({
                data: expect.objectContaining({
                    action: "comedian_deny_list.delete",
                    entityType: "comedian_deny_list",
                    entityId: "Alias Comic",
                }),
            }),
        );
    });
});

describe("PUT /api/admin/comedians", () => {
    it("updates a comedian name and regenerates the MD5 uuid", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const auditCreate = vi.fn();
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(
                makeComedian({
                    name: "tig notaro",
                    uuid: "old-uuid",
                }),
            )
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce(
                makeComedian({
                    name: "Tig Notaro",
                    uuid: "08ab8a743efbbf7f64a6bc0b8b0c3eaf",
                }),
            );
        const txQueryRaw = vi.fn().mockResolvedValueOnce([]);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: " Tig   Notaro ",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: {
                name: "Tig Notaro",
                uuid: "08ab8a743efbbf7f64a6bc0b8b0c3eaf",
            },
        });
        expect(body.comedian.name).toBe("Tig Notaro");
        expect(body.comedian.uuid).toBe("08ab8a743efbbf7f64a6bc0b8b0c3eaf");
        expect(auditCreate).toHaveBeenCalledWith(
            expect.objectContaining({
                data: expect.objectContaining({
                    action: "comedian.update",
                    entityType: "comedian",
                    entityId: "2",
                }),
            }),
        );
    });

    it("updates comedian website fields", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const auditCreate = vi.fn();
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(makeComedian())
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce(
                makeComedian({
                    website: "https://alias.example.com",
                    websiteScrapingUrl: "https://alias.example.com/tour",
                }),
            );
        const txQueryRaw = vi.fn().mockResolvedValueOnce([]);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: "Alias Comic",
                website: " https://alias.example.com ",
                websiteScrapingUrl: " https://alias.example.com/tour ",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: {
                name: "Alias Comic",
                uuid: "3e19dd3064b1dc0cf4e7d69d7f5cb762",
                website: "https://alias.example.com",
                websiteScrapingUrl: "https://alias.example.com/tour",
            },
        });
        expect(body.comedian.website).toBe("https://alias.example.com");
        expect(body.comedian.websiteScrapingUrl).toBe(
            "https://alias.example.com/tour",
        );
    });

    it("rejects updates that would collide with another comedian uuid", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(makeComedian())
            .mockResolvedValueOnce({ id: 9, name: "Tig Notaro" });
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: vi.fn(),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: "Tig Notaro",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(409);
        expect(body.error).toContain("Generated UUID already belongs to");
        expect(update).not.toHaveBeenCalled();
    });
});
