import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        $queryRaw: vi.fn(),
        $transaction: vi.fn(),
    },
}));

vi.mock("@prisma/client", () => ({
    Prisma: {
        sql: (strings: TemplateStringsArray, ...values: unknown[]) => ({
            strings: Array.from(strings),
            values,
        }),
    },
}));

import { DELETE, GET, POST } from "./route";
import { auth } from "@/auth";
import { db } from "@/lib/db";

const mockAuth = vi.mocked(auth);
const mockQueryRaw = vi.mocked(db.$queryRaw);
const mockTransaction = vi.mocked(db.$transaction);

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

function makeRequest(method: string, body?: unknown) {
    return new NextRequest("http://localhost/api/admin/deny-list", {
        method,
        headers:
            body === undefined
                ? undefined
                : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockTransaction.mockImplementation(async (callback) =>
        callback({
            $queryRaw: vi.fn(),
            adminActionAudit: {
                create: vi.fn(),
            },
        } as never),
    );
});

describe("GET /api/admin/deny-list", () => {
    it("returns 401 when auth() returns null", async () => {
        mockAuth.mockResolvedValue(null as never);

        const res = await GET();

        expect(res.status).toBe(401);
    });

    it("returns 422 when session has no profile", async () => {
        mockAuth.mockResolvedValue({ user: {} } as never);

        const res = await GET();

        expect(res.status).toBe(422);
    });

    it("returns 403 when profile.role is not admin", async () => {
        mockAuth.mockResolvedValue({
            profile: { id: "profile-2", userid: "user-2", role: "user" },
        } as never);

        const res = await GET();

        expect(res.status).toBe(403);
    });

    it("lists deny-list entries with admin context fields", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        mockQueryRaw.mockResolvedValue([
            {
                name: "Open Mic",
                reason: "Recurring event title, not a comedian",
                added_by: "profile-1",
                deleted_at: new Date("2026-05-17T20:00:00Z"),
            },
        ] as never);

        const res = await GET();
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.entries).toEqual([
            {
                name: "Open Mic",
                reason: "Recurring event title, not a comedian",
                addedBy: "profile-1",
                addedAt: "2026-05-17T20:00:00.000Z",
            },
        ]);
    });
});

describe("POST /api/admin/deny-list", () => {
    it("requires admin access", async () => {
        mockAuth.mockResolvedValue(null as never);

        const res = await POST(
            makeRequest("POST", { name: "Open Mic", reason: "x" }),
        );

        expect(res.status).toBe(401);
    });

    it("requires a non-empty name and reason", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const res = await POST(makeRequest("POST", { name: " ", reason: "" }));

        expect(res.status).toBe(400);
    });

    it("creates a deny-list row and writes an audit entry", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const auditCreate = vi.fn();
        const txQueryRaw = vi
            .fn()
            .mockResolvedValueOnce([])
            .mockResolvedValueOnce([
                {
                    name: "Open Mic",
                    reason: "Recurring event title, not a comedian",
                    added_by: "profile-1",
                    deleted_at: new Date("2026-05-17T20:00:00Z"),
                },
            ]);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await POST(
            makeRequest("POST", {
                name: "  Open Mic  ",
                reason: " Recurring event title, not a comedian ",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(201);
        expect(body.entry).toEqual({
            name: "Open Mic",
            reason: "Recurring event title, not a comedian",
            addedBy: "profile-1",
            addedAt: "2026-05-17T20:00:00.000Z",
        });
        expect(auditCreate).toHaveBeenCalledWith({
            data: {
                actorProfileId: "profile-1",
                action: "comedian_deny_list.create",
                entityType: "comedian_deny_list",
                entityId: "Open Mic",
                reason: "Recurring event title, not a comedian",
                before: {},
                after: {
                    name: "Open Mic",
                    reason: "Recurring event title, not a comedian",
                    addedBy: "profile-1",
                    addedAt: "2026-05-17T20:00:00.000Z",
                },
            },
        });
    });
});

describe("DELETE /api/admin/deny-list", () => {
    it("requires admin access", async () => {
        mockAuth.mockResolvedValue({
            profile: { id: "profile-2", userid: "user-2", role: "user" },
        } as never);

        const res = await DELETE(
            makeRequest("DELETE", { name: "Open Mic", reason: "reviewed" }),
        );

        expect(res.status).toBe(403);
    });

    it("requires a removal reason", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const res = await DELETE(
            makeRequest("DELETE", { name: "Open Mic", reason: "" }),
        );

        expect(res.status).toBe(400);
    });

    it("returns 404 when the deny-list row does not exist", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                $queryRaw: vi.fn().mockResolvedValueOnce([]),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await DELETE(
            makeRequest("DELETE", {
                name: "Open Mic",
                reason: "valid comedian",
            }),
        );

        expect(res.status).toBe(404);
    });

    it("removes a deny-list row and writes an audit entry", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const auditCreate = vi.fn();
        const before = {
            name: "Open Mic",
            reason: "Recurring event title",
            added_by: "profile-1",
            deleted_at: new Date("2026-05-17T20:00:00Z"),
        };
        const txQueryRaw = vi
            .fn()
            .mockResolvedValueOnce([before])
            .mockResolvedValueOnce([before]);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await DELETE(
            makeRequest("DELETE", {
                name: "Open Mic",
                reason: "Confirmed canonical comedian",
            }),
        );

        expect(res.status).toBe(200);
        expect(auditCreate).toHaveBeenCalledWith({
            data: {
                actorProfileId: "profile-1",
                action: "comedian_deny_list.delete",
                entityType: "comedian_deny_list",
                entityId: "Open Mic",
                reason: "Confirmed canonical comedian",
                before: {
                    name: "Open Mic",
                    reason: "Recurring event title",
                    addedBy: "profile-1",
                    addedAt: "2026-05-17T20:00:00.000Z",
                },
                after: {},
            },
        });
    });
});
