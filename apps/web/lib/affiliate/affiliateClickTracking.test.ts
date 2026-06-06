import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/lib/db", () => ({
    db: {
        show: { findUnique: vi.fn() },
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

import { GET } from "@/app/api/v1/tickets/out/route";
import { db } from "@/lib/db";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { checkRateLimit } from "@/lib/rateLimit";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockShowFindUnique = vi.mocked(db.show.findUnique as any);
const mockClickCreate = vi.mocked(db.ticketPurchaseClickEvent.create as any);
const mockCheckRateLimit = vi.mocked(checkRateLimit);

function makeOutboundRequest(destinationUrl: string): NextRequest {
    const url = new URL("http://localhost/api/v1/tickets/out");
    url.searchParams.set("showId", "42");
    url.searchParams.set("clubId", "24");
    url.searchParams.set("surface", "show_card");
    url.searchParams.set("url", destinationUrl);
    return new NextRequest(url, {
        headers: { "user-agent": "Vitest Browser" },
    });
}

describe("affiliate outbound click tracking", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockResolveAuth.mockResolvedValue(null);
        mockShowFindUnique.mockResolvedValue({ id: 42, clubId: 24 });
        mockClickCreate.mockResolvedValue({ id: 1 });
    });

    it("redirects to the routed destination and records provider, fallback, and show context", async () => {
        const res = await GET(
            makeOutboundRequest("https://www.eventbrite.com/e/show-123"),
        );

        expect(res.status).toBe(302);
        expect(res.headers.get("location")).toBe(
            "https://www.eventbrite.com/e/show-123",
        );
        expect(mockCheckRateLimit).toHaveBeenCalledWith(
            "ticket-clicks:anon-ip:203.0.113.10",
            { limit: 60, windowMs: 60_000 },
        );
        expect(mockClickCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                showId: 42,
                clubId: 24,
                profileId: null,
                destinationUrl: "https://www.eventbrite.com/e/show-123",
                routedDestinationUrl: "https://www.eventbrite.com/e/show-123",
                destinationProvider: "eventbrite",
                affiliateApplied: false,
                fallbackReason: "no_affiliate_rule",
                sourceSurface: "show_card",
                userAgent: "Vitest Browser",
            }),
        });
        const data = mockClickCreate.mock.calls[0][0].data as Record<
            string,
            unknown
        >;
        expect(data.anonymousVisitorId).toEqual(expect.any(String));
        expect(Object.keys(data)).not.toContain("ip");
        expect(res.headers.get("set-cookie")).toContain("lt_anon_visitor_id=");
    });

    it("rejects malformed destinations before writing attribution", async () => {
        const res = await GET(makeOutboundRequest("javascript:alert(1)"));
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body).toEqual({ error: "Invalid destination URL" });
        expect(mockClickCreate).not.toHaveBeenCalled();
    });
});
