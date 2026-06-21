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
        chain: null,
        scrapingSources: [],
        shows: [],
        _count: { shows: 10 },
        ...overrides,
    };
}

function makeRequest(
    body: unknown = { description: "Hi" },
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

        const [req, ctx] = makeRequest({ description: null }, "abc");
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 400 for non-JSON body", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const [req, ctx] = makeRequest("not-json-{{{");
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 400 when no editable or status field is present", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const [req, ctx] = makeRequest({});
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 404 when Prisma reports the club is missing", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        mockUpdate.mockRejectedValue({ code: "P2025" });

        const [req, ctx] = makeRequest({ description: "x" });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(404);
    });

    it("happy path: updates, revalidates, returns 200", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        mockUpdate.mockResolvedValue({
            ...clubRow({ description: "Great club" }),
        } as never);

        const [req, ctx] = makeRequest({ description: "  Great club  " });
        const res = await PATCH(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.ok).toBe(true);
        expect(body.club.name).toBe("Comedy Cellar");

        expect(mockUpdate).toHaveBeenCalledWith({
            where: { id: CLUB_ID },
            data: expect.objectContaining({
                description: "Great club",
            }),
            select: expect.objectContaining({
                id: true,
                name: true,
                description: true,
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

    it("clears the description when null is submitted", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        mockUpdate.mockResolvedValue({
            ...clubRow({ name: "Gotham", description: null }),
        } as never);

        const [req, ctx] = makeRequest({ description: null });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(200);
        expect(mockUpdate).toHaveBeenCalledWith({
            where: { id: CLUB_ID },
            data: expect.objectContaining({
                description: null,
            }),
            select: expect.objectContaining({
                id: true,
                name: true,
                description: true,
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
            }),
        );
        const update = vi.fn().mockResolvedValue(
            clubRow({
                name: "Gotham",
                description: "New",
            }),
        );
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                club: { findUnique, update },
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const [req, ctx] = makeRequest({ description: "New" });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(200);
        expect(findUnique).toHaveBeenCalledWith({
            where: { id: CLUB_ID },
            select: expect.objectContaining({
                id: true,
                name: true,
                description: true,
            }),
        });
        expect(update).toHaveBeenCalledWith({
            where: { id: CLUB_ID },
            data: expect.objectContaining({
                description: "New",
            }),
            select: expect.objectContaining({
                id: true,
                name: true,
                description: true,
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
                }),
                after: expect.objectContaining({
                    id: CLUB_ID,
                    name: "Gotham",
                    description: "New",
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

    it("accepts every intentional club type override", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        for (const clubType of [
            "club",
            "venue",
            "festival",
            "producer",
            "secret_location",
            "non_comedy",
        ]) {
            const auditCreate = vi.fn();
            const findUnique = vi.fn().mockResolvedValue(clubRow());
            const update = vi.fn().mockResolvedValue(clubRow({ clubType }));
            mockTransaction.mockImplementationOnce(async (callback) =>
                callback({
                    club: { findUnique, update },
                    adminActionAudit: { create: auditCreate },
                } as never),
            );

            const [req, ctx] = makeRequest({ clubType });
            const res = await PATCH(req, ctx);
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(body.club.clubType).toBe(clubType);
            expect(update).toHaveBeenCalledWith({
                where: { id: CLUB_ID },
                data: expect.objectContaining({ clubType }),
                select: expect.any(Object),
            });
        }
    });

    it("accepts not_open_yet as a club status override", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const auditCreate = vi.fn();
        const findUnique = vi.fn().mockResolvedValue(clubRow());
        const update = vi.fn().mockResolvedValue(
            clubRow({
                status: "not_open_yet",
            }),
        );
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                club: { findUnique, update },
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const [req, ctx] = makeRequest({
            status: "not_open_yet",
        });
        const res = await PATCH(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.club.status).toBe("not_open_yet");
        expect(update).toHaveBeenCalledWith({
            where: { id: CLUB_ID },
            data: expect.objectContaining({
                status: "not_open_yet",
            }),
            select: expect.any(Object),
        });
    });

    it("updates a club name and revalidates the old and new names", async () => {
        mockAuth.mockResolvedValue(adminSession as never);

        const auditCreate = vi.fn();
        const findUnique = vi.fn().mockResolvedValue(clubRow());
        const update = vi.fn().mockResolvedValue(
            clubRow({
                name: "Comedy Cellar Village Underground",
            }),
        );
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                club: { findUnique, update },
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const [req, ctx] = makeRequest({
            name: " Comedy   Cellar Village Underground ",
        });
        const res = await PATCH(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.club.name).toBe("Comedy Cellar Village Underground");
        expect(update).toHaveBeenCalledWith({
            where: { id: CLUB_ID },
            data: expect.objectContaining({
                name: "Comedy Cellar Village Underground",
            }),
            select: expect.any(Object),
        });
        expect(auditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                action: "club.update",
                entityType: "club",
                entityId: String(CLUB_ID),
            }),
        });
        const calledTags = mockRevalidateTag.mock.calls.map((c) => c[0]);
        expect(calledTags).toEqual(
            expect.arrayContaining([
                "Comedy Cellar",
                "Comedy Cellar Village Underground",
            ]),
        );
    });
});
