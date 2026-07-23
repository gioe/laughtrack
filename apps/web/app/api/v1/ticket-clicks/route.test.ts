import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/lib/db", () => ({
    db: {
        show: { findUnique: vi.fn() },
        discoveryImpressionEvent: { findUnique: vi.fn() },
        ticketPurchaseClickEvent: { create: vi.fn() },
        $queryRaw: vi.fn(),
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

vi.mock("@/lib/auth/requireAdmin", () => ({
    requireAdminForApi: vi.fn(() =>
        Promise.resolve({
            ok: true,
            context: { userId: "user-1", profileId: "profile-1" },
        }),
    ),
}));

import { GET, POST } from "./route";
import { db } from "@/lib/db";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { checkRateLimit, getClientIp } from "@/lib/rateLimit";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockCheckRateLimit = vi.mocked(checkRateLimit);
const mockRequireAdminForApi = vi.mocked(requireAdminForApi);
const mockShowFindUnique = vi.mocked(db.show.findUnique as any);
const mockImpressionFindUnique = vi.mocked(
    db.discoveryImpressionEvent.findUnique as any,
);
const mockClickCreate = vi.mocked(db.ticketPurchaseClickEvent.create as any);
const mockQueryRaw = vi.mocked(db.$queryRaw as any);

function makePost(body: unknown, headers: Record<string, string> = {}) {
    return new NextRequest("http://localhost/api/v1/ticket-clicks", {
        method: "POST",
        headers: {
            "content-type": "application/json",
            "user-agent": "Vitest Browser",
            ...headers,
        },
        body: JSON.stringify(body),
    });
}

const IMPRESSION_ID = "550e8400-e29b-41d4-a716-446655440000";

describe("/api/v1/ticket-clicks", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockResolveAuth.mockResolvedValue(null);
        mockShowFindUnique.mockResolvedValue({ id: 42, clubId: 24 });
        mockClickCreate.mockResolvedValue({
            id: 1,
        });
        mockImpressionFindUnique.mockResolvedValue(null);
        mockQueryRaw.mockResolvedValue([
            {
                total_clicks: BigInt(3),
                unique_signed_in_users: BigInt(2),
                unique_anonymous_visitors: BigInt(1),
            },
        ]);
    });

    it("records anonymous clicks with a durable opaque visitor id and no raw IP field", async () => {
        const res = await POST(
            makePost({
                showId: 42,
                clubId: 24,
                destinationUrl: "https://tickets.example.com/buy",
                sourceSurface: "show_detail",
                deviceMetadata: { platform: "web" },
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(201);
        expect(body).toEqual({ ok: true });
        expect(mockCheckRateLimit).toHaveBeenCalledWith(
            "ticket-clicks:anon-ip:203.0.113.10",
            { limit: 60, windowMs: 60_000 },
        );
        expect(mockClickCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                showId: 42,
                clubId: 24,
                profileId: null,
                destinationUrl: "https://tickets.example.com/buy",
                sourceSurface: "show_detail",
                userAgent: "Vitest Browser",
                deviceMetadata: { platform: "web" },
            }),
        });
        const data = mockClickCreate.mock.calls[0][0].data as Record<
            string,
            unknown
        >;
        expect(data.anonymousVisitorId).toEqual(expect.any(String));
        expect(Object.keys(data)).not.toContain("ip");
        expect(getClientIp).toHaveBeenCalled();
        expect(res.headers.get("set-cookie")).toContain("lt_anon_visitor_id=");
    });

    it("records signed-in clicks against the resolved profile and existing anonymous visitor id", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });

        await POST(
            makePost(
                {
                    showId: 42,
                    clubId: 24,
                    destinationUrl: "https://tickets.example.com/buy",
                    sourceSurface: "show_card",
                },
                { cookie: "lt_anon_visitor_id=anon-existing" },
            ),
        );

        expect(mockCheckRateLimit).toHaveBeenCalledWith(
            "ticket-clicks:profile:profile-1",
            { limit: 60, windowMs: 60_000 },
        );
        expect(mockClickCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                profileId: "profile-1",
                anonymousVisitorId: "anon-existing",
                sourceSurface: "show_card",
            }),
        });
    });

    it("retains authoritative discovery attribution for the owning signed-in profile", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockImpressionFindUnique.mockResolvedValue({
            eventId: IMPRESSION_ID,
            entityType: "show",
            entityId: 42,
            profileId: "profile-1",
            anonymousVisitorId: null,
            surface: "near_you",
            policyVersion: "near-you-v2",
            experimentVariant: "candidate",
            rank: 3,
        });

        const res = await POST(
            makePost({
                showId: 42,
                clubId: 24,
                destinationUrl: "https://tickets.example.com/buy",
                sourceSurface: "show_card",
                impressionId: IMPRESSION_ID,
            }),
        );

        expect(res.status).toBe(201);
        expect(mockImpressionFindUnique).toHaveBeenCalledWith({
            where: { eventId: IMPRESSION_ID },
            select: {
                eventId: true,
                entityType: true,
                entityId: true,
                profileId: true,
                anonymousVisitorId: true,
                surface: true,
                policyVersion: true,
                experimentVariant: true,
                rank: true,
            },
        });
        expect(mockClickCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                discoveryImpressionEventId: IMPRESSION_ID,
                discoverySurface: "near_you",
                discoveryPolicyVersion: "near-you-v2",
                discoveryExperimentVariant: "candidate",
                discoveryRank: 3,
            }),
        });
    });

    it("accepts attribution owned by the existing anonymous visitor cookie", async () => {
        mockImpressionFindUnique.mockResolvedValue({
            eventId: IMPRESSION_ID,
            entityType: "show",
            entityId: 42,
            profileId: null,
            anonymousVisitorId: "anon-existing",
            surface: "near_you",
            policyVersion: "near-you-v2",
            experimentVariant: "explore",
            rank: 7,
        });

        const res = await POST(
            makePost(
                {
                    showId: 42,
                    clubId: 24,
                    destinationUrl: "https://tickets.example.com/buy",
                    sourceSurface: "show_card",
                    impressionId: IMPRESSION_ID,
                },
                { cookie: "lt_anon_visitor_id=anon-existing" },
            ),
        );

        expect(res.status).toBe(201);
        expect(mockClickCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                discoveryImpressionEventId: IMPRESSION_ID,
                discoveryExperimentVariant: "explore",
            }),
        });
    });

    it.each([
        {
            reason: "belongs to another actor",
            impression: {
                eventId: IMPRESSION_ID,
                entityType: "show",
                entityId: 42,
                profileId: "profile-other",
                anonymousVisitorId: "anon-other",
                surface: "near_you",
                policyVersion: "near-you-v2",
                experimentVariant: "candidate",
                rank: 3,
            },
        },
        {
            reason: "belongs to another show",
            impression: {
                eventId: IMPRESSION_ID,
                entityType: "show",
                entityId: 99,
                profileId: "profile-1",
                anonymousVisitorId: null,
                surface: "near_you",
                policyVersion: "near-you-v2",
                experimentVariant: "candidate",
                rank: 3,
            },
        },
    ])("rejects supplied attribution that $reason", async ({ impression }) => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockImpressionFindUnique.mockResolvedValue(impression);

        const res = await POST(
            makePost({
                showId: 42,
                clubId: 24,
                destinationUrl: "https://tickets.example.com/buy",
                sourceSurface: "show_card",
                impressionId: IMPRESSION_ID,
            }),
        );

        expect(res.status).toBe(400);
        expect(await res.json()).toEqual({
            error: "Invalid discovery impression attribution",
        });
        expect(mockClickCreate).not.toHaveBeenCalled();
    });

    it("rejects a malformed supplied impression id without querying it", async () => {
        const res = await POST(
            makePost({
                showId: 42,
                clubId: 24,
                destinationUrl: "https://tickets.example.com/buy",
                sourceSurface: "show_card",
                impressionId: "not-a-uuid",
            }),
        );

        expect(res.status).toBe(400);
        expect(mockImpressionFindUnique).not.toHaveBeenCalled();
        expect(mockClickCreate).not.toHaveBeenCalled();
    });

    it("rejects mismatched club ids instead of trusting the client supplied association", async () => {
        mockShowFindUnique.mockResolvedValue({ id: 42, clubId: 99 });

        const res = await POST(
            makePost({
                showId: 42,
                clubId: 24,
                destinationUrl: "https://tickets.example.com/buy",
                sourceSurface: "show_detail",
            }),
        );

        expect(res.status).toBe(400);
        expect(mockClickCreate).not.toHaveBeenCalled();
    });

    it("reports total clicks and unique signed-in and anonymous visitors for date/show/club filters", async () => {
        const res = await GET(
            new NextRequest(
                "http://localhost/api/v1/ticket-clicks?from=2026-05-01&to=2026-05-31&showId=42&clubId=24",
            ),
        );
        const body = await res.json();

        expect(mockRequireAdminForApi).toHaveBeenCalled();
        expect(res.status).toBe(200);
        expect(body).toEqual({
            totalClicks: 3,
            uniqueSignedInUsers: 2,
            uniqueAnonymousVisitors: 1,
        });
    });
});
