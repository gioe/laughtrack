import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        $queryRaw: vi.fn(),
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

import { GET, POST } from "./route";
import { auth } from "@/auth";
import { db } from "@/lib/db";

const mockAuth = vi.mocked(auth);
const mockQueryRaw = vi.mocked(db.$queryRaw);

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

function makePostRequest(body: unknown) {
    return new NextRequest("http://localhost/api/admin/insights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: typeof body === "string" ? body : JSON.stringify(body),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.mockResolvedValue(adminSession as never);
});

describe("GET /api/admin/insights", () => {
    it("requires admin access", async () => {
        mockAuth.mockResolvedValue(null as never);

        const res = await GET();

        expect(res.status).toBe(401);
    });

    it("lists curated insight definitions without query text", async () => {
        const res = await GET();
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.insights).toEqual(
            expect.arrayContaining([
                expect.objectContaining({
                    name: "clubs.search",
                    primitive: "clubs",
                    parameters: expect.arrayContaining([
                        expect.objectContaining({ name: "q", type: "string" }),
                        expect.objectContaining({
                            name: "limit",
                            type: "integer",
                        }),
                    ]),
                }),
                expect.objectContaining({
                    name: "shows.upcoming",
                    primitive: "shows",
                }),
            ]),
        );
        expect(JSON.stringify(body.insights).toLowerCase()).not.toContain(
            "select ",
        );
    });

    it("covers the initial admin primitives", async () => {
        const res = await GET();
        const body = await res.json();

        expect(
            new Set(
                body.insights.map(
                    (insight: { primitive: string }) => insight.primitive,
                ),
            ),
        ).toEqual(
            new Set([
                "clubs",
                "shows",
                "comedians",
                "tickets",
                "scrapingSources",
                "tags",
                "users",
                "podcasts",
                "emailSubscriptions",
            ]),
        );
    });
});

describe("POST /api/admin/insights", () => {
    it("rejects arbitrary SQL-shaped insight names", async () => {
        const res = await POST(
            makePostRequest({
                insight: "SELECT * FROM users",
                params: { limit: 10 },
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.error).toBe("Unknown insight");
        expect(mockQueryRaw).not.toHaveBeenCalled();
    });

    it("rejects invalid parameters before running a query", async () => {
        const res = await POST(
            makePostRequest({
                insight: "clubs.search",
                params: { q: "Gotham", limit: 500 },
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.error).toBe("Invalid parameters");
        expect(mockQueryRaw).not.toHaveBeenCalled();
    });

    it("runs a representative primitive through its curated query builder", async () => {
        mockQueryRaw.mockResolvedValue([
            {
                id: 42,
                name: "Gotham Comedy Club",
                city: "New York",
                state: "NY",
                visible: true,
                totalShows: 7,
            },
        ] as never);

        const res = await POST(
            makePostRequest({
                insight: "clubs.search",
                params: { q: "Gotham", limit: 5 },
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({
            ok: true,
            insight: "clubs.search",
            rows: [
                {
                    id: 42,
                    name: "Gotham Comedy Club",
                    city: "New York",
                    state: "NY",
                    visible: true,
                    totalShows: 7,
                },
            ],
        });
        expect(mockQueryRaw).toHaveBeenCalledTimes(1);
        expect(mockQueryRaw.mock.calls[0][0]).toMatchObject({
            strings: expect.arrayContaining([
                expect.stringContaining("FROM clubs"),
            ]),
            values: expect.arrayContaining(["%Gotham%", 5]),
        });
    });
});
