import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/lib/metrics", () => ({
    withRequestMetrics: <T>(handler: T) => handler,
}));

vi.mock("@/lib/db", () => ({
    db: {
        discoveryImpressionEvent: { findMany: vi.fn() },
        discoveryEngagementEvent: { createMany: vi.fn() },
    },
}));

vi.mock("@/lib/auth/resolveAuth", () => ({
    PROFILE_MISSING: "PROFILE_MISSING",
    resolveAuth: vi.fn(),
}));

vi.mock("@/lib/rateLimit", () => ({
    RATE_LIMITS: {
        authenticated: { limit: 100, windowMs: 60_000 },
        unauthenticated: { limit: 20, windowMs: 60_000 },
    },
    checkRateLimit: vi.fn(() =>
        Promise.resolve({
            allowed: true,
            limit: 20,
            remaining: 19,
            resetAt: 1_800_000_000_000,
        }),
    ),
    getClientIp: vi.fn(() => "203.0.113.10"),
    rateLimitHeaders: vi.fn(() => ({ "X-RateLimit-Remaining": "19" })),
    rateLimitResponse: vi.fn(() => new NextResponse(null, { status: 429 })),
}));

import { POST } from "./route";
import { db } from "@/lib/db";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { checkRateLimit } from "@/lib/rateLimit";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockCheckRateLimit = vi.mocked(checkRateLimit);
const mockImpressionFindMany = vi.mocked(
    db.discoveryImpressionEvent.findMany as any,
);
const mockEngagementCreateMany = vi.mocked(
    db.discoveryEngagementEvent.createMany as any,
);

const EVENT_ID = "550e8400-e29b-41d4-a716-446655440001";
const IMPRESSION_ID = "550e8400-e29b-41d4-a716-446655440000";

function validEvent(overrides: Record<string, unknown> = {}) {
    return {
        eventId: EVENT_ID,
        impressionEventId: IMPRESSION_ID,
        engagementType: "show_detail",
        engagedAt: new Date().toISOString(),
        ...overrides,
    };
}

function makeRequest(
    body: unknown,
    headers: Record<string, string> = {},
): NextRequest {
    return new NextRequest("http://localhost/api/v1/discovery/engagements", {
        method: "POST",
        headers: { "content-type": "application/json", ...headers },
        body: JSON.stringify(body),
    });
}

describe("POST /api/v1/discovery/engagements", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockResolveAuth.mockResolvedValue(null);
        mockImpressionFindMany.mockResolvedValue([
            {
                eventId: IMPRESSION_ID,
                profileId: null,
                anonymousVisitorId: "anon-existing",
            },
        ]);
        mockEngagementCreateMany.mockResolvedValue({ count: 1 });
    });

    it("records an anonymous show-detail engagement for an owned impression", async () => {
        const response = await POST(
            makeRequest(
                { events: [validEvent()] },
                {
                    cookie: "lt_anon_visitor_id=anon-existing",
                    "user-agent": "Do not persist me",
                },
            ),
        );

        expect(response.status).toBe(201);
        expect(await response.json()).toEqual({ accepted: 1, inserted: 1 });
        expect(mockImpressionFindMany).toHaveBeenCalledWith({
            where: { eventId: { in: [IMPRESSION_ID] } },
            select: {
                eventId: true,
                profileId: true,
                anonymousVisitorId: true,
            },
        });
        expect(mockEngagementCreateMany).toHaveBeenCalledWith({
            data: [
                {
                    eventId: EVENT_ID,
                    impressionEventId: IMPRESSION_ID,
                    engagementType: "show_detail",
                    engagedAt: expect.any(Date),
                },
            ],
            skipDuplicates: true,
        });
        const stored = mockEngagementCreateMany.mock.calls[0][0]
            .data[0] as Record<string, unknown>;
        expect(stored).not.toHaveProperty("ip");
        expect(stored).not.toHaveProperty("userAgent");
        expect(response.headers.get("set-cookie")).toBeNull();
    });

    it("accepts ownership through the authenticated profile", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockImpressionFindMany.mockResolvedValue([
            {
                eventId: IMPRESSION_ID,
                profileId: "profile-1",
                anonymousVisitorId: "older-anon-id",
            },
        ]);

        const response = await POST(
            makeRequest(
                { events: [validEvent()] },
                { cookie: "lt_anon_visitor_id=current-anon-id" },
            ),
        );

        expect(response.status).toBe(201);
        expect(mockCheckRateLimit).toHaveBeenCalledWith(
            "discovery-engagements:profile:profile-1",
            { limit: 100, windowMs: 60_000 },
        );
        expect(mockEngagementCreateMany).toHaveBeenCalledOnce();
    });

    it("treats duplicate engagement event ids as an idempotent success", async () => {
        mockEngagementCreateMany.mockResolvedValue({ count: 0 });

        const response = await POST(
            makeRequest(
                { events: [validEvent()] },
                { cookie: "lt_anon_visitor_id=anon-existing" },
            ),
        );

        expect(response.status).toBe(201);
        expect(await response.json()).toEqual({ accepted: 1, inserted: 0 });
    });

    it.each([
        ["empty batch", { events: [] }],
        [
            "oversized batch",
            { events: Array.from({ length: 51 }, () => validEvent()) },
        ],
        ["invalid event id", { events: [validEvent({ eventId: "nope" })] }],
        [
            "invalid impression id",
            { events: [validEvent({ impressionEventId: "nope" })] },
        ],
        [
            "invalid engagement type",
            { events: [validEvent({ engagementType: "favorite" })] },
        ],
        [
            "event older than 24 hours",
            {
                events: [
                    validEvent({
                        engagedAt: new Date(
                            Date.now() - 24 * 60 * 60 * 1000 - 1_000,
                        ).toISOString(),
                    }),
                ],
            },
        ],
        [
            "event over five minutes in the future",
            {
                events: [
                    validEvent({
                        engagedAt: new Date(
                            Date.now() + 5 * 60 * 1000 + 1_000,
                        ).toISOString(),
                    }),
                ],
            },
        ],
    ])("rejects %s", async (_label, body) => {
        const response = await POST(makeRequest(body));

        expect(response.status).toBe(400);
        expect(mockImpressionFindMany).not.toHaveBeenCalled();
        expect(mockEngagementCreateMany).not.toHaveBeenCalled();
    });

    it("rejects missing and cross-actor impressions", async () => {
        mockImpressionFindMany.mockResolvedValue([
            {
                eventId: IMPRESSION_ID,
                profileId: "another-profile",
                anonymousVisitorId: "another-anon-id",
            },
        ]);

        const response = await POST(
            makeRequest(
                { events: [validEvent()] },
                { cookie: "lt_anon_visitor_id=anon-existing" },
            ),
        );

        expect(response.status).toBe(400);
        expect(mockEngagementCreateMany).not.toHaveBeenCalled();
    });

    it("returns 429 before impression lookup or persistence", async () => {
        mockCheckRateLimit.mockResolvedValue({
            allowed: false,
            limit: 20,
            remaining: 0,
            resetAt: Date.now() + 60_000,
        });

        const response = await POST(
            makeRequest(
                { events: [validEvent()] },
                { cookie: "lt_anon_visitor_id=anon-existing" },
            ),
        );

        expect(response.status).toBe(429);
        expect(mockImpressionFindMany).not.toHaveBeenCalled();
        expect(mockEngagementCreateMany).not.toHaveBeenCalled();
    });
});
