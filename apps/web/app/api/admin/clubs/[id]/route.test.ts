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
        $transaction: vi.fn(async (callback) =>
            callback({
                club: {
                    findUnique: vi.fn(),
                    update: vi.fn(),
                },
                adminActionAudit: {
                    create: vi.fn(),
                },
            }),
        ),
        club: {
            update: vi.fn(),
        },
    },
}));

vi.mock("@prisma/client", () => ({
    Prisma: {
        DbNull: Symbol.for("Prisma.DbNull"),
        PrismaClientKnownRequestError: class PrismaClientKnownRequestError extends Error {
            code: string;
            constructor(message: string, opts: { code: string }) {
                super(message);
                this.code = opts.code;
            }
        },
        prismaVersion: { client: "test" },
    },
}));

vi.mock("next/cache", () => ({
    revalidateTag: vi.fn(),
}));

import { PATCH } from "./route";
import { auth } from "@/auth";
import { db } from "@/lib/db";
import { revalidateTag } from "next/cache";

const mockAuth = vi.mocked(auth);
const mockUpdate = vi.mocked(db.club.update);
const mockTransaction = vi.mocked(db.$transaction);
const mockFindUserProfile = vi.mocked(db.userProfile.findFirst);
const mockRevalidateTag = vi.mocked(revalidateTag);

const CLUB_ID = 42;

function clubRow(overrides: Record<string, unknown> = {}) {
    return {
        id: CLUB_ID,
        name: "Comedy Cellar",
        city: "New York",
        state: "NY",
        website: "https://example.com",
        visible: true,
        status: "active",
        clubType: "club",
        closedAt: null,
        totalShows: 10,
        description: "Old description",
        hours: null,
        chain: null,
        scrapingSources: [],
        shows: [],
        _count: { shows: 10 },
        ...overrides,
    };
}

function makeRequest(
    body: unknown = { description: "Hi", hours: null },
    id: string = String(CLUB_ID),
): [NextRequest, { params: Promise<{ id: string }> }] {
    const req = new NextRequest(`http://localhost/api/admin/clubs/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: typeof body === "string" ? body : JSON.stringify(body),
    });
    return [req, { params: Promise.resolve({ id }) }];
}

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

beforeEach(() => {
    vi.clearAllMocks();
    mockFindUserProfile.mockResolvedValue({
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    } as never);
    mockTransaction.mockImplementation(async (callback) =>
        callback({
            club: {
                findUnique: vi.fn().mockResolvedValue(clubRow()),
                update: mockUpdate,
            },
            adminActionAudit: {
                create: vi.fn(),
            },
        } as never),
    );
});

describe("PATCH /api/admin/clubs/[id]", () => {
    it("returns 401 when auth() returns null", async () => {
        mockAuth.mockResolvedValue(null as never);

        const [req, ctx] = makeRequest();
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(401);
    });

    it("returns 422 when session has no profile", async () => {
        mockAuth.mockResolvedValue({ user: {} } as never);

        const [req, ctx] = makeRequest();
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(422);
    });

    it("returns 403 when profile.role !== 'admin'", async () => {
        mockAuth.mockResolvedValue({
            profile: { id: "p", userid: "u", role: "user" },
        } as never);
        mockFindUserProfile.mockResolvedValue({
            id: "p",
            userid: "u",
            role: "user",
        } as never);

        const [req, ctx] = makeRequest();
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(403);
    });

    it("returns 400 for invalid club id", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const [req, ctx] = makeRequest(
            { description: null, hours: null },
            "abc",
        );
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 400 for non-JSON body", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const [req, ctx] = makeRequest("not-json-{{{");
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 400 when hours has unknown day", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const [req, ctx] = makeRequest({
            description: null,
            hours: { funday: "9-5" },
        });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 400 when description is missing from payload", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const [req, ctx] = makeRequest({ hours: null });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 404 when Prisma reports the club is missing", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        mockUpdate.mockRejectedValue({ code: "P2025" });

        const [req, ctx] = makeRequest({ description: "x", hours: null });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(404);
    });

    it("happy path: updates, revalidates, returns 200", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        mockUpdate.mockResolvedValue({
            ...clubRow({
                description: "Great club",
                hours: { monday: "Closed", tuesday: "7 PM - 11 PM" },
            }),
        } as never);

        const hours = {
            monday: "Closed",
            tuesday: "7 PM - 11 PM",
            wednesday: "",
            thursday: "",
            friday: "",
            saturday: "",
            sunday: "",
        };
        const [req, ctx] = makeRequest({
            description: "  Great club  ",
            hours,
        });
        const res = await PATCH(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.ok).toBe(true);
        expect(body.club.name).toBe("Comedy Cellar");

        expect(mockUpdate).toHaveBeenCalledWith({
            where: { id: CLUB_ID },
            data: expect.objectContaining({
                description: "Great club",
                hours: { monday: "Closed", tuesday: "7 PM - 11 PM" },
            }),
            select: expect.objectContaining({
                id: true,
                name: true,
                description: true,
                hours: true,
            }),
        });
        expect(mockTransaction).toHaveBeenCalledTimes(1);

        const calledTags = mockRevalidateTag.mock.calls.map((c) => c[0]);
        expect(calledTags).toEqual(
            expect.arrayContaining([
                "club-detail-data",
                "club-metadata",
                "Comedy Cellar",
            ]),
        );
    });

    it("passes Prisma.DbNull when hours is null", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        mockUpdate.mockResolvedValue({
            ...clubRow({ name: "Gotham", description: null, hours: null }),
        } as never);

        const [req, ctx] = makeRequest({ description: null, hours: null });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(200);
        expect(mockUpdate).toHaveBeenCalledWith({
            where: { id: CLUB_ID },
            data: expect.objectContaining({
                description: null,
                hours: Symbol.for("Prisma.DbNull"),
            }),
            select: expect.objectContaining({
                id: true,
                name: true,
                description: true,
                hours: true,
            }),
        });
    });

    it("writes the club update audit row in the same transaction", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const auditCreate = vi.fn();
        const findUnique = vi.fn().mockResolvedValue(
            clubRow({
                name: "Gotham",
                description: "Old",
                hours: { monday: "Closed" },
            }),
        );
        const update = vi.fn().mockResolvedValue(
            clubRow({
                name: "Gotham",
                description: "New",
                hours: { monday: "7 PM - 11 PM" },
            }),
        );
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                club: { findUnique, update },
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const [req, ctx] = makeRequest({
            description: "New",
            hours: {
                monday: "7 PM - 11 PM",
                tuesday: "",
                wednesday: "",
                thursday: "",
                friday: "",
                saturday: "",
                sunday: "",
            },
        });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(200);
        expect(findUnique).toHaveBeenCalledWith({
            where: { id: CLUB_ID },
            select: expect.objectContaining({
                id: true,
                name: true,
                description: true,
                hours: true,
            }),
        });
        expect(update).toHaveBeenCalledWith({
            where: { id: CLUB_ID },
            data: expect.objectContaining({
                description: "New",
                hours: { monday: "7 PM - 11 PM" },
            }),
            select: expect.objectContaining({
                id: true,
                name: true,
                description: true,
                hours: true,
            }),
        });
        expect(auditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                actorProfileId: "profile-1",
                action: "club.update",
                entityType: "club",
                entityId: String(CLUB_ID),
                reason: null,
                before: expect.objectContaining({
                    id: CLUB_ID,
                    name: "Gotham",
                    description: "Old",
                    hours: { monday: "Closed" },
                }),
                after: expect.objectContaining({
                    id: CLUB_ID,
                    name: "Gotham",
                    description: "New",
                    hours: { monday: "7 PM - 11 PM" },
                }),
            }),
        });
    });

    it("updates club status overrides and audits them", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const auditCreate = vi.fn();
        const findUnique = vi.fn().mockResolvedValue(clubRow());
        const update = vi.fn().mockResolvedValue(
            clubRow({
                visible: false,
                status: "closed",
                clubType: "festival",
                closedAt: new Date("2026-05-19T00:00:00.000Z"),
            }),
        );
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                club: { findUnique, update },
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const [req, ctx] = makeRequest({
            visible: false,
            status: "closed",
            clubType: "festival",
            closedAt: "2026-05-19",
        });
        const res = await PATCH(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.club.visible).toBe(false);
        expect(body.club.status).toBe("closed");
        expect(update).toHaveBeenCalledWith({
            where: { id: CLUB_ID },
            data: expect.objectContaining({
                visible: false,
                status: "closed",
                clubType: "festival",
                closedAt: new Date("2026-05-19T00:00:00.000Z"),
            }),
            select: expect.any(Object),
        });
        expect(auditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                action: "club.status_override",
                entityType: "club",
                entityId: String(CLUB_ID),
            }),
        });
    });
});
