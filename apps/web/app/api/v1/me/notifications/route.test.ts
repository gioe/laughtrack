import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));

vi.mock("@/lib/rateLimit", () => ({
    checkRateLimit: vi.fn(() => ({
        allowed: true,
        limit: 100,
        remaining: 99,
        resetAt: 0,
    })),
    getClientIp: vi.fn(() => "127.0.0.1"),
    RATE_LIMITS: { authenticated: {}, authToken: {} },
    rateLimitHeaders: vi.fn(() => ({ "X-RateLimit-Remaining": "99" })),
    rateLimitResponse: vi.fn(
        () => new Response(null, { status: 429 }) as never,
    ),
}));

vi.mock("@/lib/db", () => ({
    db: {
        userProfile: {
            findUnique: vi.fn(),
            update: vi.fn(),
        },
        sentNotification: {
            findMany: vi.fn(),
        },
    },
}));

import { GET, PATCH } from "./route";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { checkRateLimit } from "@/lib/rateLimit";
import { db } from "@/lib/db";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockCheckRateLimit = vi.mocked(checkRateLimit);
const mockUpdateProfile = vi.mocked(db.userProfile.update);
const mockFindProfile = vi.mocked(db.userProfile.findUnique);
const mockFindNotifications = vi.mocked(db.sentNotification.findMany);

function makeRequest(body: unknown): NextRequest {
    return new NextRequest("http://localhost/api/v1/me/notifications", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockCheckRateLimit.mockResolvedValue({
        allowed: true,
        limit: 100,
        remaining: 99,
        resetAt: 0,
    });
});

describe("PATCH /api/v1/me/notifications", () => {
    it("returns 401 when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const res = await PATCH(makeRequest({ pushShowNotifications: true }));

        expect(res.status).toBe(401);
        expect(mockUpdateProfile).not.toHaveBeenCalled();
    });

    it("returns 422 when authenticated user has no UserProfile row", async () => {
        mockResolveAuth.mockResolvedValue(PROFILE_MISSING);

        const res = await PATCH(makeRequest({ pushShowNotifications: true }));

        expect(res.status).toBe(422);
        expect(await res.json()).toEqual({ error: "profile_missing" });
        expect(mockUpdateProfile).not.toHaveBeenCalled();
    });

    it("rejects requests without a supported notification field", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-123",
            profileId: "profile-123",
        });

        const res = await PATCH(makeRequest({}));

        expect(res.status).toBe(400);
        expect(await res.json()).toEqual({
            error: "At least one notification preference must be provided",
        });
        expect(mockUpdateProfile).not.toHaveBeenCalled();
    });

    it("updates email and push notification preferences for the authenticated profile", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-123",
            profileId: "profile-123",
        });
        mockUpdateProfile.mockResolvedValue({
            emailShowNotifications: true,
            pushShowNotifications: false,
        } as never);

        const res = await PATCH(
            makeRequest({
                emailShowNotifications: true,
                pushShowNotifications: false,
            }),
        );

        expect(res.status).toBe(200);
        expect(mockUpdateProfile).toHaveBeenCalledWith({
            where: { userid: "user-123" },
            data: {
                emailShowNotifications: true,
                pushShowNotifications: false,
            },
            select: {
                emailShowNotifications: true,
                pushShowNotifications: true,
            },
        });
        expect(await res.json()).toEqual({
            data: {
                emailShowNotifications: true,
                pushShowNotifications: false,
            },
        });
    });

    it("returns 429 before auth when the IP rate limit is exceeded", async () => {
        mockCheckRateLimit.mockResolvedValueOnce({
            allowed: false,
            limit: 10,
            remaining: 0,
            resetAt: 0,
        });

        const res = await PATCH(makeRequest({ pushShowNotifications: true }));

        expect(res.status).toBe(429);
        expect(mockResolveAuth).not.toHaveBeenCalled();
    });
});

function makeGetRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/me/notifications", {
        method: "GET",
    });
}

function notificationRow(overrides: Record<string, unknown> = {}) {
    return {
        comedianId: "comedian-uuid-1",
        showId: 555,
        notificationType: "push",
        notificationGroupId: null,
        sentAt: new Date("2026-06-20T12:00:00.000Z"),
        comedian: {
            name: "Taylor Tomlinson",
            hasImage: true,
            imageAssets: [
                {
                    avatarPath: "comedian-images/taylor/avatar.webp",
                    heroPath: "comedian-images/taylor/hero.webp",
                    isActive: true,
                },
            ],
        },
        show: {
            date: new Date("2026-07-01T02:00:00.000Z"),
            showPageUrl: "https://laugh-track.com/show/555",
            club: {
                name: "The Comedy Store",
                city: "Los Angeles",
                state: "CA",
                timezone: "America/Los_Angeles",
            },
        },
        ...overrides,
    };
}

describe("GET /api/v1/me/notifications", () => {
    beforeEach(() => {
        mockFindProfile.mockResolvedValue({
            notificationsLastSeenAt: null,
        } as never);
        mockFindNotifications.mockResolvedValue([] as never);
    });

    it("returns 401 when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const res = await GET(makeGetRequest());

        expect(res.status).toBe(401);
        expect(mockFindNotifications).not.toHaveBeenCalled();
    });

    it("returns 422 when authenticated user has no UserProfile row", async () => {
        mockResolveAuth.mockResolvedValue(PROFILE_MISSING);

        const res = await GET(makeGetRequest());

        expect(res.status).toBe(422);
        expect(await res.json()).toEqual({ error: "profile_missing" });
        expect(mockFindNotifications).not.toHaveBeenCalled();
    });

    it("returns 429 when the pre-auth IP rate limit is exceeded", async () => {
        mockCheckRateLimit.mockResolvedValueOnce({
            allowed: false,
            limit: 10,
            remaining: 0,
            resetAt: 0,
        });

        const res = await GET(makeGetRequest());

        expect(res.status).toBe(429);
        expect(mockResolveAuth).not.toHaveBeenCalled();
    });

    it("returns 429 when the per-user rate limit is exceeded", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-1",
            profileId: "profile-1",
        });
        mockCheckRateLimit
            .mockResolvedValueOnce({
                allowed: true,
                limit: 10,
                remaining: 9,
                resetAt: 0,
            })
            .mockResolvedValueOnce({
                allowed: false,
                limit: 100,
                remaining: 0,
                resetAt: 0,
            });

        const res = await GET(makeGetRequest());

        expect(res.status).toBe(429);
        expect(mockFindNotifications).not.toHaveBeenCalled();
    });

    it("returns an empty feed with zero unread when no notifications exist", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-1",
            profileId: "profile-1",
        });

        const res = await GET(makeGetRequest());

        expect(res.status).toBe(200);
        expect(await res.json()).toEqual({
            data: { items: [], unreadCount: 0, lastSeenAt: null },
        });
        expect(mockFindNotifications).toHaveBeenCalledWith(
            expect.objectContaining({
                where: { userId: "user-1" },
                orderBy: { sentAt: "desc" },
            }),
        );
    });

    it("reconstructs the title/body and exposes show + club fields", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-1",
            profileId: "profile-1",
        });
        mockFindNotifications.mockResolvedValue([notificationRow()] as never);

        const res = await GET(makeGetRequest());

        const body = await res.json();
        expect(body.data.items).toHaveLength(1);
        expect(body.data.items[0]).toMatchObject({
            id: "legacy:comedian-uuid-1:555",
            title: "Taylor Tomlinson is performing near you",
            body: "The Comedy Store on Tuesday, June 30 at 7:00 pm PDT",
            comedianId: "comedian-uuid-1",
            comedianName: "Taylor Tomlinson",
            comedianImageUrl:
                "https://test.b-cdn.net/comedian-images/taylor/avatar.webp",
            route: null,
            channels: ["push"],
            isUnread: true,
        });
        // Single-show entry: show details live in shows[0].
        expect(body.data.items[0].shows).toHaveLength(1);
        expect(body.data.items[0].shows[0]).toMatchObject({
            showId: 555,
            showPageUrl: "https://laugh-track.com/show/555",
            subtitle: "The Comedy Store on Tuesday, June 30 at 7:00 pm PDT",
            clubName: "The Comedy Store",
            city: "Los Angeles",
            state: "CA",
        });
    });

    it("groups multiple shows for one comedian into a single tiered entry", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-1",
            profileId: "profile-1",
        });
        const groupId = "run-abc";
        mockFindNotifications.mockResolvedValue([
            notificationRow({
                notificationGroupId: groupId,
                showId: 555,
                show: {
                    date: new Date("2026-07-01T02:00:00.000Z"),
                    showPageUrl: "https://laugh-track.com/show/555",
                    club: {
                        name: "The Comedy Store",
                        city: "Los Angeles",
                        state: "CA",
                        timezone: "America/Los_Angeles",
                    },
                },
            }),
            notificationRow({
                notificationGroupId: groupId,
                showId: 556,
                show: {
                    date: new Date("2026-07-05T02:00:00.000Z"),
                    showPageUrl: "https://laugh-track.com/show/556",
                    club: {
                        name: "The Comedy Store",
                        city: "Los Angeles",
                        state: "CA",
                        timezone: "America/Los_Angeles",
                    },
                },
            }),
        ] as never);

        const res = await GET(makeGetRequest());

        const body = await res.json();
        expect(body.data.items).toHaveLength(1);
        expect(body.data.items[0]).toMatchObject({
            id: groupId,
            title: "Taylor Tomlinson has 2 shows near you",
            route: "favorites",
            body: "The Comedy Store",
        });
        expect(
            body.data.items[0].shows.map((s: { showId: number }) => s.showId),
        ).toEqual([555, 556]);
        expect(body.data.items[0].comedians).toHaveLength(1);
    });

    it("groups multiple comedians in a run into a digest entry", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-1",
            profileId: "profile-1",
        });
        const groupId = "run-xyz";
        mockFindNotifications.mockResolvedValue([
            notificationRow({
                notificationGroupId: groupId,
                comedianId: "comedian-uuid-1",
                showId: 555,
                show: {
                    date: new Date("2026-07-01T02:00:00.000Z"),
                    showPageUrl: "https://laugh-track.com/show/555",
                    club: {
                        name: "The Comedy Store",
                        city: "Los Angeles",
                        state: "CA",
                        timezone: "America/Los_Angeles",
                    },
                },
            }),
            notificationRow({
                notificationGroupId: groupId,
                comedianId: "comedian-uuid-2",
                showId: 556,
                comedian: {
                    name: "Ian Fidance",
                    hasImage: false,
                    imageAssets: [],
                },
                show: {
                    date: new Date("2026-07-05T02:00:00.000Z"),
                    showPageUrl: "https://laugh-track.com/show/556",
                    club: {
                        name: "The Stand",
                        city: "New York",
                        state: "NY",
                        timezone: "America/New_York",
                    },
                },
            }),
        ] as never);

        const res = await GET(makeGetRequest());

        const body = await res.json();
        expect(body.data.items).toHaveLength(1);
        expect(body.data.items[0]).toMatchObject({
            id: groupId,
            title: "2 comedians you follow have shows near you",
            route: "favorites",
            body: "The Comedy Store, The Stand",
        });
        expect(body.data.items[0].comedians).toHaveLength(2);
        expect(body.data.items[0].shows).toHaveLength(2);
    });

    it("collapses email + push rows for the same (comedian, show) into one item", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-1",
            profileId: "profile-1",
        });
        mockFindNotifications.mockResolvedValue([
            notificationRow({
                notificationType: "push",
                sentAt: new Date("2026-06-20T12:00:00.000Z"),
            }),
            notificationRow({
                notificationType: "email",
                sentAt: new Date("2026-06-20T11:00:00.000Z"),
            }),
        ] as never);

        const res = await GET(makeGetRequest());

        const body = await res.json();
        expect(body.data.items).toHaveLength(1);
        expect(body.data.items[0].channels).toEqual(["push", "email"]);
        // The latest send (push at 12:00) wins as the item timestamp.
        expect(body.data.items[0].sentAt).toBe("2026-06-20T12:00:00.000Z");
        expect(body.data.unreadCount).toBe(1);
    });

    it("marks items at or before lastSeenAt as read and counts only unread", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-1",
            profileId: "profile-1",
        });
        mockFindProfile.mockResolvedValue({
            notificationsLastSeenAt: new Date("2026-06-20T12:30:00.000Z"),
        } as never);
        mockFindNotifications.mockResolvedValue([
            notificationRow({
                comedianId: "comedian-uuid-2",
                showId: 777,
                sentAt: new Date("2026-06-20T13:00:00.000Z"),
            }),
            notificationRow({
                comedianId: "comedian-uuid-1",
                showId: 555,
                sentAt: new Date("2026-06-20T12:00:00.000Z"),
            }),
        ] as never);

        const res = await GET(makeGetRequest());

        const body = await res.json();
        expect(body.data.lastSeenAt).toBe("2026-06-20T12:30:00.000Z");
        expect(body.data.unreadCount).toBe(1);
        const byId = Object.fromEntries(
            body.data.items.map((i: { id: string; isUnread: boolean }) => [
                i.id,
                i.isUnread,
            ]),
        );
        expect(byId["legacy:comedian-uuid-2:777"]).toBe(true);
        expect(byId["legacy:comedian-uuid-1:555"]).toBe(false);
    });

    it("sorts items by newest notification send time, then soonest show time", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-1",
            profileId: "profile-1",
        });
        mockFindNotifications.mockResolvedValue([
            notificationRow({
                showId: 101,
                sentAt: new Date("2026-06-20T12:00:00.000Z"),
                show: {
                    date: new Date("2026-08-10T02:00:00.000Z"),
                    showPageUrl: "https://laugh-track.com/show/101",
                    club: {
                        name: "Late Show Club",
                        city: "Los Angeles",
                        state: "CA",
                        timezone: "America/Los_Angeles",
                    },
                },
            }),
            notificationRow({
                showId: 103,
                sentAt: new Date("2026-06-20T12:00:00.000Z"),
                show: {
                    date: new Date("2026-07-01T02:00:00.000Z"),
                    showPageUrl: "https://laugh-track.com/show/103",
                    club: {
                        name: "Sooner Show Club",
                        city: "Los Angeles",
                        state: "CA",
                        timezone: "America/Los_Angeles",
                    },
                },
            }),
            notificationRow({
                showId: 102,
                sentAt: new Date("2026-06-20T13:00:00.000Z"),
                show: {
                    date: new Date("2026-09-01T02:00:00.000Z"),
                    showPageUrl: "https://laugh-track.com/show/102",
                    club: {
                        name: "Newest Send Club",
                        city: "Los Angeles",
                        state: "CA",
                        timezone: "America/Los_Angeles",
                    },
                },
            }),
        ] as never);

        const res = await GET(makeGetRequest());

        const body = await res.json();
        expect(
            body.data.items.map(
                (item: { shows: { showId: number }[] }) => item.shows[0].showId,
            ),
        ).toEqual([102, 103, 101]);
    });

    it("falls back gracefully when comedian/club fields are missing", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-1",
            profileId: "profile-1",
        });
        mockFindNotifications.mockResolvedValue([
            notificationRow({
                comedian: { name: null },
                show: {
                    date: null,
                    showPageUrl: "https://laugh-track.com/show/555",
                    club: { name: "Mystery Room", city: null, state: null },
                },
            }),
        ] as never);

        const res = await GET(makeGetRequest());

        const body = await res.json();
        expect(body.data.items[0].title).toBe(
            "A comedian you follow is performing near you",
        );
        expect(body.data.items[0].body).toBe("Mystery Room");
        expect(body.data.items[0].shows[0].showDate).toBeNull();
    });

    it("does not leave a dangling separator when the club name is empty", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-1",
            profileId: "profile-1",
        });
        mockFindNotifications.mockResolvedValue([
            notificationRow({
                show: {
                    date: null,
                    showPageUrl: "https://laugh-track.com/show/555",
                    club: { name: "", city: "Los Angeles", state: "CA" },
                },
            }),
        ] as never);

        const res = await GET(makeGetRequest());

        const body = await res.json();
        expect(body.data.items[0].title).toBe(
            "Taylor Tomlinson is performing near you",
        );
        expect(body.data.items[0].body).toBe("");
    });

    it("caps the history fetch with a take limit", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-1",
            profileId: "profile-1",
        });

        await GET(makeGetRequest());

        expect(mockFindNotifications).toHaveBeenCalledWith(
            expect.objectContaining({ take: 100 }),
        );
    });
});
