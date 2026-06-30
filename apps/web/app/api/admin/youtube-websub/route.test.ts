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
        youTubeWebSubSetting: {
            findUnique: vi.fn(),
            upsert: vi.fn(),
        },
    },
}));

vi.mock("@/lib/admin/audit", () => ({
    writeAdminActionAudit: vi.fn(() => Promise.resolve({})),
}));

vi.mock("@/lib/admin/youtubeWebSub", () => ({
    getYouTubeWebSubAdminData: vi.fn(),
    getYouTubeWebSubEvent: vi.fn(),
}));

import { GET, PATCH } from "./route";
import { auth } from "@/auth";
import { db } from "@/lib/db";
import { writeAdminActionAudit } from "@/lib/admin/audit";
import {
    getYouTubeWebSubAdminData,
    getYouTubeWebSubEvent,
} from "@/lib/admin/youtubeWebSub";

const mockAuth = vi.mocked(auth);
const mockFindProfile = vi.mocked(db.userProfile.findFirst);
const mockTransaction = vi.mocked(db.$transaction);
const mockUpsert = vi.mocked(db.youTubeWebSubSetting.upsert);
const mockFindUniqueSetting = vi.mocked(db.youTubeWebSubSetting.findUnique);
const mockAudit = vi.mocked(writeAdminActionAudit);
const mockAdminData = vi.mocked(getYouTubeWebSubAdminData);
const mockGetEvent = vi.mocked(getYouTubeWebSubEvent);

const adminSession = {
    profile: { id: "profile-1", userid: "user-1", role: "admin" },
};

function makeGet(query = "") {
    return new NextRequest(
        `http://localhost/api/admin/youtube-websub${query}`,
        { method: "GET" },
    );
}

function makePatch(body?: unknown) {
    return new NextRequest("http://localhost/api/admin/youtube-websub", {
        method: "PATCH",
        headers:
            body === undefined
                ? undefined
                : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.mockResolvedValue(adminSession as never);
    mockFindProfile.mockResolvedValue({
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    } as never);
});

describe("GET /api/admin/youtube-websub", () => {
    it("returns 401 when not signed in", async () => {
        mockAuth.mockResolvedValueOnce(null as never);
        const res = await GET(makeGet());
        expect(res.status).toBe(401);
    });

    it("returns 403 for non-admins", async () => {
        mockFindProfile.mockResolvedValueOnce({
            id: "profile-1",
            userid: "user-1",
            role: "user",
        } as never);
        const res = await GET(makeGet());
        expect(res.status).toBe(403);
    });

    it("returns the full admin dataset when no eventId is given", async () => {
        const data = {
            settings: { feedIngestionEnabled: true, pushDeliveryEnabled: false },
            comedians: [],
            events: [{ id: 1 }],
        };
        mockAdminData.mockResolvedValueOnce(data as never);
        const res = await GET(makeGet());
        expect(res.status).toBe(200);
        expect(await res.json()).toEqual(data);
    });

    it("returns a single event detail when eventId is given", async () => {
        const event = { id: 7, payloadXml: "<feed/>" };
        mockGetEvent.mockResolvedValueOnce(event as never);
        const res = await GET(makeGet("?eventId=7"));
        expect(res.status).toBe(200);
        expect(await res.json()).toEqual({ event });
        expect(mockGetEvent).toHaveBeenCalledWith(7);
    });

    it("returns 400 for a non-numeric eventId", async () => {
        const res = await GET(makeGet("?eventId=abc"));
        expect(res.status).toBe(400);
        expect(mockGetEvent).not.toHaveBeenCalled();
    });

    it("returns 404 when the event does not exist", async () => {
        mockGetEvent.mockResolvedValueOnce(null);
        const res = await GET(makeGet("?eventId=99"));
        expect(res.status).toBe(404);
    });
});

describe("PATCH /api/admin/youtube-websub", () => {
    it("rejects an empty payload", async () => {
        const res = await PATCH(makePatch({}));
        expect(res.status).toBe(400);
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("upserts the singleton setting and writes an audit row", async () => {
        const after = {
            feedIngestionEnabled: true,
            pushDeliveryEnabled: false,
        };
        mockFindUniqueSetting.mockResolvedValueOnce({
            feedIngestionEnabled: false,
            pushDeliveryEnabled: false,
        } as never);
        mockUpsert.mockResolvedValueOnce(after as never);
        mockTransaction.mockImplementationOnce(((
            cb: (tx: typeof db) => unknown,
        ) => cb(db)) as never);

        const res = await PATCH(makePatch({ feedIngestionEnabled: true }));

        expect(res.status).toBe(200);
        expect(await res.json()).toEqual({ ok: true, settings: after });
        expect(mockUpsert).toHaveBeenCalledWith(
            expect.objectContaining({
                where: { id: 1 },
                create: { id: 1, feedIngestionEnabled: true },
                update: { feedIngestionEnabled: true },
            }),
        );
        expect(mockAudit).toHaveBeenCalledWith(
            db,
            expect.objectContaining({
                action: "youtube_websub_settings.update",
                entityType: "youtube_websub_settings",
                entityId: 1,
                after,
            }),
        );
    });

    it("returns 401 for an unauthenticated PATCH", async () => {
        mockAuth.mockResolvedValueOnce(null as never);
        const res = await PATCH(makePatch({ pushDeliveryEnabled: true }));
        expect(res.status).toBe(401);
        expect(mockTransaction).not.toHaveBeenCalled();
    });
});
