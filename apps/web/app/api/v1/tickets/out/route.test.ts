import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/lib/db", () => ({
    db: {
        show: { findUnique: vi.fn() },
        discoveryImpressionEvent: { findUnique: vi.fn() },
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
const mockImpressionFindUnique = vi.mocked(
    db.discoveryImpressionEvent.findUnique as any,
);
const mockClickCreate = vi.mocked(db.ticketPurchaseClickEvent.create as any);

function makeGet(params: Record<string, string>) {
    const search = new URLSearchParams(params).toString();
    return new NextRequest(`http://localhost/api/v1/tickets/out?${search}`, {
        headers: { "user-agent": "Vitest Browser" },
    });
}

const IMPRESSION_ID = "550e8400-e29b-41d4-a716-446655440000";

describe("/api/v1/tickets/out", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockResolveAuth.mockResolvedValue(null);
        mockShowFindUnique.mockResolvedValue({
            id: 42,
            clubId: 24,
            tickets: [
                { purchaseUrl: "https://tickets.example.com/buy?ref=abc" },
            ],
        });
        mockClickCreate.mockResolvedValue({ id: 1 });
        mockImpressionFindUnique.mockResolvedValue(null);
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
        expect(mockShowFindUnique).toHaveBeenCalledWith({
            where: { id: 42 },
            select: {
                id: true,
                clubId: true,
                tickets: { select: { purchaseUrl: true } },
            },
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

    it("retains authoritative discovery attribution for an owned impression", async () => {
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
            rank: 2,
        });

        const res = await GET(
            makeGet({
                showId: "42",
                clubId: "24",
                surface: "show_detail",
                url: "https://tickets.example.com/event/99",
                impressionId: IMPRESSION_ID,
            }),
        );

        expect(res.status).toBe(302);
        expect(mockClickCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                discoveryImpressionEventId: IMPRESSION_ID,
                discoverySurface: "near_you",
                discoveryPolicyVersion: "near-you-v2",
                discoveryExperimentVariant: "candidate",
                discoveryRank: 2,
            }),
        });
    });

    it("retries concurrent first-anonymous attribution and adopts its visitor cookie", async () => {
        mockImpressionFindUnique
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce({
                eventId: IMPRESSION_ID,
                entityType: "show",
                entityId: 42,
                profileId: null,
                anonymousVisitorId: "anon-from-impression",
                surface: "near_you",
                policyVersion: "near-you-control-v1",
                experimentVariant: "control",
                rank: 1,
            });

        const res = await GET(
            makeGet({
                showId: "42",
                clubId: "24",
                surface: "compact_show_card",
                url: "https://tickets.example.com/event/99",
                impressionId: IMPRESSION_ID,
            }),
        );

        expect(res.status).toBe(302);
        expect(mockImpressionFindUnique).toHaveBeenCalledTimes(2);
        expect(res.headers.get("set-cookie")).toContain(
            "lt_anon_visitor_id=anon-from-impression",
        );
        expect(mockClickCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                anonymousVisitorId: "anon-from-impression",
                discoveryImpressionEventId: IMPRESSION_ID,
                discoveryRank: 1,
            }),
        });
    });

    it("redirects and records an unattributed click when supplied attribution is invalid", async () => {
        mockImpressionFindUnique.mockResolvedValue({
            eventId: IMPRESSION_ID,
            entityType: "show",
            entityId: 999,
            profileId: null,
            anonymousVisitorId: "anon-other",
            surface: "near_you",
            policyVersion: "near-you-v2",
            experimentVariant: "candidate",
            rank: 2,
        });

        const res = await GET(
            makeGet({
                showId: "42",
                clubId: "24",
                surface: "show_detail",
                url: "https://tickets.example.com/event/99",
                impressionId: IMPRESSION_ID,
            }),
        );

        expect(res.status).toBe(302);
        expect(res.headers.get("location")).toBe(
            "https://tickets.example.com/event/99",
        );
        expect(mockClickCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                discoveryImpressionEventId: null,
                discoverySurface: null,
                discoveryPolicyVersion: null,
                discoveryExperimentVariant: null,
                discoveryRank: null,
            }),
        });
    });

    it("does not query a malformed optional impression id and still redirects", async () => {
        const res = await GET(
            makeGet({
                showId: "42",
                clubId: "24",
                surface: "show_detail",
                url: "https://tickets.example.com/event/99",
                impressionId: "not-a-uuid",
            }),
        );

        expect(res.status).toBe(302);
        expect(mockImpressionFindUnique).not.toHaveBeenCalled();
        expect(mockClickCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                discoveryImpressionEventId: null,
            }),
        });
    });

    it("400s when the show has only null purchaseUrls so no origin can be validated", async () => {
        mockShowFindUnique.mockResolvedValue({
            id: 42,
            clubId: 24,
            tickets: [{ purchaseUrl: null }],
        });

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
