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

import { PATCH } from "./route";
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
        popularity: 12,
        totalShows: 1,
        parentComedianId: null,
        parentComedian: null,
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
});
