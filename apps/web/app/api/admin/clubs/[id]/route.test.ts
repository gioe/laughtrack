import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        club: {
            update: vi.fn(),
        },
    },
}));

vi.mock("@prisma/client", () => ({
    Prisma: { DbNull: Symbol.for("Prisma.DbNull") },
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
const mockRevalidateTag = vi.mocked(revalidateTag);

const CLUB_ID = 42;

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
});

describe("PATCH /api/admin/clubs/[id]", () => {
    it("returns 401 when auth() returns null", async () => {
        mockAuth.mockResolvedValue(null as any);

        const [req, ctx] = makeRequest();
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(401);
    });

    it("returns 422 when session has no profile", async () => {
        mockAuth.mockResolvedValue({ user: {} } as any);

        const [req, ctx] = makeRequest();
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(422);
    });

    it("returns 403 when profile.role !== 'admin'", async () => {
        mockAuth.mockResolvedValue({
            profile: { id: "p", userid: "u", role: "user" },
        } as any);

        const [req, ctx] = makeRequest();
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(403);
    });

    it("returns 400 for invalid club id", async () => {
        mockAuth.mockResolvedValue(adminSession as any);

        const [req, ctx] = makeRequest(
            { description: null, hours: null },
            "abc",
        );
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 400 for non-JSON body", async () => {
        mockAuth.mockResolvedValue(adminSession as any);

        const [req, ctx] = makeRequest("not-json-{{{");
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 400 when hours has unknown day", async () => {
        mockAuth.mockResolvedValue(adminSession as any);

        const [req, ctx] = makeRequest({
            description: null,
            hours: { funday: "9-5" },
        });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 400 when description is missing from payload", async () => {
        mockAuth.mockResolvedValue(adminSession as any);

        const [req, ctx] = makeRequest({ hours: null });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(400);
    });

    it("returns 404 when Prisma reports the club is missing", async () => {
        mockAuth.mockResolvedValue(adminSession as any);
        mockUpdate.mockRejectedValue({ code: "P2025" });

        const [req, ctx] = makeRequest({ description: "x", hours: null });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(404);
    });

    it("happy path: updates, revalidates, returns 200", async () => {
        mockAuth.mockResolvedValue(adminSession as any);
        mockUpdate.mockResolvedValue({
            id: CLUB_ID,
            name: "Comedy Cellar",
        } as any);

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
            select: { id: true, name: true },
        });

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
        mockAuth.mockResolvedValue(adminSession as any);
        mockUpdate.mockResolvedValue({
            id: CLUB_ID,
            name: "Gotham",
        } as any);

        const [req, ctx] = makeRequest({ description: null, hours: null });
        const res = await PATCH(req, ctx);

        expect(res.status).toBe(200);
        expect(mockUpdate).toHaveBeenCalledWith({
            where: { id: CLUB_ID },
            data: expect.objectContaining({
                description: null,
                hours: Symbol.for("Prisma.DbNull"),
            }),
            select: { id: true, name: true },
        });
    });
});
