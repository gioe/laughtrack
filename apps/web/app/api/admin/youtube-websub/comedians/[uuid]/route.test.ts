import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/metrics", () => ({
    withRequestMetrics: <T>(handler: T) => handler,
}));

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        userProfile: { findFirst: vi.fn() },
        $transaction: vi.fn(),
        comedian: {
            findUnique: vi.fn(),
            update: vi.fn(),
        },
    },
}));

vi.mock("@/lib/admin/audit", () => ({
    writeAdminActionAudit: vi.fn(() => Promise.resolve({})),
}));

import { PATCH } from "./route";
import { auth } from "@/auth";
import { db } from "@/lib/db";
import { writeAdminActionAudit } from "@/lib/admin/audit";

const mockAuth = vi.mocked(auth);
const mockFindProfile = vi.mocked(db.userProfile.findFirst);
const mockTransaction = vi.mocked(db.$transaction);
const mockFindComedian = vi.mocked(db.comedian.findUnique);
const mockUpdateComedian = vi.mocked(db.comedian.update);
const mockAudit = vi.mocked(writeAdminActionAudit);

const adminSession = {
    profile: { id: "profile-1", userid: "user-1", role: "admin" },
};

function makePatch(uuid: string, body?: unknown) {
    const req = new NextRequest(
        `http://localhost/api/admin/youtube-websub/comedians/${uuid}`,
        {
            method: "PATCH",
            headers:
                body === undefined
                    ? undefined
                    : { "Content-Type": "application/json" },
            body: body === undefined ? undefined : JSON.stringify(body),
        },
    );
    return [req, { params: Promise.resolve({ uuid }) }] as const;
}

beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.mockResolvedValue(adminSession as never);
    mockFindProfile.mockResolvedValue({
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    } as never);
    mockTransaction.mockImplementation(((cb: (tx: typeof db) => unknown) =>
        cb(db)) as never);
});

describe("PATCH /api/admin/youtube-websub/comedians/[uuid]", () => {
    it("returns 403 for non-admins", async () => {
        mockFindProfile.mockResolvedValueOnce({
            id: "profile-1",
            userid: "user-1",
            role: "user",
        } as never);
        const res = await PATCH(
            ...makePatch("abc", { youtubeLiveFeedEnabled: true }),
        );
        expect(res.status).toBe(403);
    });

    it("rejects an empty payload", async () => {
        const res = await PATCH(...makePatch("abc", {}));
        expect(res.status).toBe(400);
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("updates flags, writes audit, and returns the comedian", async () => {
        const before = {
            uuid: "abc",
            name: "Jane Comic",
            youtubeLiveFeedEnabled: false,
            youtubeLiveNotificationsEnabled: false,
        };
        const after = { ...before, youtubeLiveFeedEnabled: true };
        mockFindComedian.mockResolvedValueOnce(before as never);
        mockUpdateComedian.mockResolvedValueOnce(after as never);

        const res = await PATCH(
            ...makePatch("abc", { youtubeLiveFeedEnabled: true }),
        );

        expect(res.status).toBe(200);
        expect(await res.json()).toEqual({ ok: true, comedian: after });
        expect(mockUpdateComedian).toHaveBeenCalledWith(
            expect.objectContaining({
                where: { uuid: "abc" },
                data: { youtubeLiveFeedEnabled: true },
            }),
        );
        expect(mockAudit).toHaveBeenCalledWith(
            db,
            expect.objectContaining({
                action: "youtube_websub_comedian_flags.update",
                entityType: "comedian",
                entityId: "abc",
                before,
                after,
            }),
        );
    });

    it("returns 404 when the comedian is missing", async () => {
        mockFindComedian.mockResolvedValueOnce(null);
        const res = await PATCH(
            ...makePatch("missing", { youtubeLiveFeedEnabled: true }),
        );
        expect(res.status).toBe(404);
        expect(mockUpdateComedian).not.toHaveBeenCalled();
    });
});
