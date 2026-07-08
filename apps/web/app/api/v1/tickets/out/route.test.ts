import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/lib/db", () => ({
    db: {
        show: { findUnique: vi.fn() },
        ticket: { findMany: vi.fn() },
        ticketPurchaseClickEvent: { create: vi.fn() },
    },
}));

vi.mock("@/lib/auth/resolveAuth", () => ({
    PROFILE_MISSING: "PROFILE_MISSING",
    resolveAuth: vi.fn(),
}));

vi.mock("@/lib/rateLimit", () => ({
    RATE_LIMITS: { publicRead: { limit: 60, windowMs: 60_000 } },
    checkRateLimit: vi.fn(() =>
        Promise.resolve({
            allowed: true,
            limit: 60,
            remaining: 59,
            resetAt: 1_800_000_000_000,
        }),
    ),
    getClientIp: vi.fn(() => "203.0.113.10"),
    rateLimitHeaders: vi.fn(() => ({ "X-RateLimit-Remaining": "59" })),
    rateLimitResponse: vi.fn(() => new NextResponse(null, { status: 429 })),
}));

import { GET } from "./route";
import { db } from "@/lib/db";
import { resolveAuth } from "@/lib/auth/resolveAuth";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockShowFindUnique = vi.mocked(db.show.findUnique as any);
const mockTicketFindMany = vi.mocked(db.ticket.findMany as any);
const mockClickCreate = vi.mocked(db.ticketPurchaseClickEvent.create as any);

function makeGet(params: Record<string, string>) {
    const search = new URLSearchParams(params).toString();
    return new NextRequest(`http://localhost/api/v1/tickets/out?${search}`, {
        headers: { "user-agent": "Vitest Browser" },
    });
}

describe("/api/v1/tickets/out", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockResolveAuth.mockResolvedValue(null);
        mockShowFindUnique.mockResolvedValue({ id: 42, clubId: 24 });
        mockTicketFindMany.mockResolvedValue([
            { purchaseUrl: "https://tickets.example.com/buy?ref=abc" },
        ]);
        mockClickCreate.mockResolvedValue({ id: 1 });
    });

    it("302s and records the click when the url origin matches a show ticket purchaseUrl", async () => {
        const res = await GET(
            makeGet({
                showId: "42",
                clubId: "24",
                surface: "show_detail",
                url: "https://tickets.example.com/event/99",
            }),
        );

        expect(res.status).toBe(302);
        expect(res.headers.get("location")).toBe(
            "https://tickets.example.com/event/99",
        );
        expect(mockTicketFindMany).toHaveBeenCalledWith({
            where: { showId: 42 },
            select: { purchaseUrl: true },
        });
        expect(mockClickCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                showId: 42,
                clubId: 24,
                destinationUrl: "https://tickets.example.com/event/99",
                routedDestinationUrl: "https://tickets.example.com/event/99",
                sourceSurface: "show_detail",
            }),
        });
        expect(res.headers.get("set-cookie")).toContain("lt_anon_visitor_id=");
    });

    it("400s without redirecting or recording when the url origin does not match any ticket purchaseUrl", async () => {
        const res = await GET(
            makeGet({
                showId: "42",
                clubId: "24",
                surface: "show_detail",
                url: "https://phishing.evil.com/steal",
            }),
        );

        expect(res.status).toBe(400);
        expect(res.headers.get("location")).toBeNull();
        expect(mockClickCreate).not.toHaveBeenCalled();
    });

    it("400s when the show has only null purchaseUrls so no origin can be validated", async () => {
        mockTicketFindMany.mockResolvedValue([{ purchaseUrl: null }]);

        const res = await GET(
            makeGet({
                showId: "42",
                clubId: "24",
                surface: "show_detail",
                url: "https://tickets.example.com/event/99",
            }),
        );

        expect(res.status).toBe(400);
        expect(mockClickCreate).not.toHaveBeenCalled();
    });
});
