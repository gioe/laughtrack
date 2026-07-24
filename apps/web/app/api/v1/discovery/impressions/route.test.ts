import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/lib/metrics", () => ({
    withRequestMetrics: <T>(handler: T) => handler,
}));

vi.mock("@/lib/db", () => ({
    db: {
        show: { findMany: vi.fn() },
        discoveryImpressionEvent: { createMany: vi.fn() },
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
import { checkRateLimit, getClientIp } from "@/lib/rateLimit";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockCheckRateLimit = vi.mocked(checkRateLimit);
const mockShowFindMany = vi.mocked(db.show.findMany as any);
const mockImpressionCreateMany = vi.mocked(
    db.discoveryImpressionEvent.createMany as any,
);

const EVENT_ID = "550e8400-e29b-41d4-a716-446655440000";

function validEvent(overrides: Record<string, unknown> = {}) {
    return {
        eventId: EVENT_ID,
        entityType: "show",
        entityId: 42,
        surface: "near_you",
        policyVersion: "near-you-v1",
        experimentVariant: "control",
        rank: 1,
        impressedAt: new Date().toISOString(),
        assignmentEligible: true,
        assignmentReason: "stable_actor_assignment",
        explorationSelected: false,
        distanceMiles: 4.2,
        maxDistanceMiles: 25,
        availabilityAtImpression: "available",
        featureVersion: "show-features-v1",
        ...overrides,
    };
}

function makeRequest(
    body: unknown,
    headers: Record<string, string> = {},
): NextRequest {
    return new NextRequest("http://localhost/api/v1/discovery/impressions", {
        method: "POST",
        headers: { "content-type": "application/json", ...headers },
        body: JSON.stringify(body),
    });
}

describe("POST /api/v1/discovery/impressions", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockResolveAuth.mockResolvedValue(null);
        mockShowFindMany.mockResolvedValue([{ id: 42 }]);
        mockImpressionCreateMany.mockResolvedValue({ count: 1 });
    });

    it("records validated anonymous batches without retaining IP or user-agent data", async () => {
        const response = await POST(
            makeRequest(
                { events: [validEvent()] },
                { "user-agent": "Do not persist me" },
            ),
        );

        expect(response.status).toBe(201);
        expect(await response.json()).toEqual({ accepted: 1, inserted: 1 });
        expect(mockCheckRateLimit).toHaveBeenCalledWith(
            "discovery-impressions:anon-ip:203.0.113.10",
            { limit: 20, windowMs: 60_000 },
        );
        expect(mockShowFindMany).toHaveBeenCalledWith({
            where: { id: { in: [42] } },
            select: { id: true },
        });
        expect(mockImpressionCreateMany).toHaveBeenCalledWith({
            data: [
                expect.objectContaining({
                    eventId: EVENT_ID,
                    entityType: "show",
                    entityId: 42,
                    surface: "near_you",
                    policyVersion: "near-you-v1",
                    experimentVariant: "control",
                    rank: 1,
                    assignmentEligible: true,
                    assignmentReason: "stable_actor_assignment",
                    explorationSelected: false,
                    distanceMiles: 4.2,
                    maxDistanceMiles: 25,
                    availabilityAtImpression: "available",
                    featureVersion: "show-features-v1",
                    profileId: null,
                    anonymousVisitorId: expect.any(String),
                    impressedAt: expect.any(Date),
                }),
            ],
            skipDuplicates: true,
        });
        const stored = mockImpressionCreateMany.mock.calls[0][0]
            .data[0] as Record<string, unknown>;
        expect(stored).not.toHaveProperty("ip");
        expect(stored).not.toHaveProperty("userAgent");
        expect(response.headers.get("set-cookie")).toContain(
            "lt_anon_visitor_id=",
        );
        expect(getClientIp).toHaveBeenCalled();
    });

    it("uses the authenticated quota and preserves the existing opaque visitor id", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });

        const response = await POST(
            makeRequest(
                { events: [validEvent()] },
                { cookie: "lt_anon_visitor_id=anon-existing" },
            ),
        );

        expect(response.status).toBe(201);
        expect(mockCheckRateLimit).toHaveBeenCalledWith(
            "discovery-impressions:profile:profile-1",
            { limit: 100, windowMs: 60_000 },
        );
        expect(mockImpressionCreateMany).toHaveBeenCalledWith({
            data: [
                expect.objectContaining({
                    profileId: "profile-1",
                    anonymousVisitorId: "anon-existing",
                }),
            ],
            skipDuplicates: true,
        });
        expect(response.headers.get("set-cookie")).toBeNull();
        expect(getClientIp).not.toHaveBeenCalled();
    });

    it("treats duplicate event ids as an idempotent success", async () => {
        mockImpressionCreateMany.mockResolvedValue({ count: 0 });

        const response = await POST(makeRequest({ events: [validEvent()] }));

        expect(response.status).toBe(201);
        expect(await response.json()).toEqual({ accepted: 1, inserted: 0 });
        expect(mockImpressionCreateMany).toHaveBeenCalledWith(
            expect.objectContaining({ skipDuplicates: true }),
        );
    });

    it.each([
        ["empty batch", { events: [] }],
        [
            "oversized batch",
            { events: Array.from({ length: 51 }, () => validEvent()) },
        ],
        ["invalid event id", { events: [validEvent({ eventId: "nope" })] }],
        [
            "invalid entity type",
            { events: [validEvent({ entityType: "comedian" })] },
        ],
        ["invalid entity id", { events: [validEvent({ entityId: 0 })] }],
        ["invalid surface", { events: [validEvent({ surface: "search" })] }],
        [
            "invalid policy",
            { events: [validEvent({ policyVersion: "has spaces" })] },
        ],
        [
            "invalid variant",
            { events: [validEvent({ experimentVariant: "treatment" })] },
        ],
        ["invalid rank", { events: [validEvent({ rank: 0 })] }],
        ["rank over 1000", { events: [validEvent({ rank: 1001 })] }],
        [
            "assignment mismatch",
            {
                events: [
                    validEvent({
                        assignmentEligible: false,
                        assignmentReason: "stable_actor_assignment",
                    }),
                ],
            },
        ],
        [
            "bootstrap candidate",
            {
                events: [
                    validEvent({
                        assignmentEligible: false,
                        assignmentReason: "cookieless_bootstrap",
                        experimentVariant: "candidate",
                    }),
                ],
            },
        ],
        [
            "exploration control",
            {
                events: [validEvent({ explorationSelected: true })],
            },
        ],
        [
            "negative distance",
            {
                events: [validEvent({ distanceMiles: -1 })],
            },
        ],
        [
            "invalid availability",
            {
                events: [validEvent({ availabilityAtImpression: "sold_out" })],
            },
        ],
        [
            "event older than 24 hours",
            {
                events: [
                    validEvent({
                        impressedAt: new Date(
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
                        impressedAt: new Date(
                            Date.now() + 5 * 60 * 1000 + 1_000,
                        ).toISOString(),
                    }),
                ],
            },
        ],
    ])("rejects %s", async (_label, body) => {
        const response = await POST(makeRequest(body));

        expect(response.status).toBe(400);
        expect(mockShowFindMany).not.toHaveBeenCalled();
        expect(mockImpressionCreateMany).not.toHaveBeenCalled();
    });

    it("rejects a batch when any referenced show does not exist", async () => {
        mockShowFindMany.mockResolvedValue([]);

        const response = await POST(makeRequest({ events: [validEvent()] }));

        expect(response.status).toBe(400);
        expect(mockImpressionCreateMany).not.toHaveBeenCalled();
    });

    it("returns 429 before entity validation or persistence", async () => {
        mockCheckRateLimit.mockResolvedValue({
            allowed: false,
            limit: 20,
            remaining: 0,
            resetAt: Date.now() + 60_000,
        });

        const response = await POST(makeRequest({ events: [validEvent()] }));

        expect(response.status).toBe(429);
        expect(mockShowFindMany).not.toHaveBeenCalled();
        expect(mockImpressionCreateMany).not.toHaveBeenCalled();
    });
});
