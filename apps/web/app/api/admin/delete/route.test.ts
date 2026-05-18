import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        $transaction: vi.fn(),
        userProfile: {
            findFirst: vi.fn(),
        },
    },
}));

vi.mock("next/cache", () => ({
    revalidateTag: vi.fn(),
}));

import { DELETE, POST } from "./route";
import { auth } from "@/auth";
import { db } from "@/lib/db";
import { revalidateTag } from "next/cache";

const mockAuth = vi.mocked(auth);
const mockTransaction = vi.mocked(db.$transaction);
const mockFindUserProfile = vi.mocked(db.userProfile.findFirst);
const mockRevalidateTag = vi.mocked(revalidateTag);

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

const club = {
    id: 42,
    name: "Gotham Comedy Club",
    address: "208 W 23rd St",
    website: "https://gothamcomedyclub.com",
    visible: true,
    totalShows: 7,
    status: "active",
};

const clubDependencies = [
    { key: "shows", label: "Shows", count: 2 },
    { key: "tickets", label: "Tickets", count: 3 },
    { key: "lineupItems", label: "Lineup items", count: 4 },
    { key: "taggedShows", label: "Show tags", count: 5 },
    { key: "showNotifications", label: "Sent notifications", count: 6 },
    { key: "scrapingSources", label: "Scraping sources", count: 1 },
];

const clubConfirmation = {
    entityType: "club",
    entityId: 42,
    label: "Gotham Comedy Club",
    dependencies: clubDependencies,
};

const podcast = {
    id: 77,
    slug: "good-one",
    source: "spotify",
    sourcePodcastId: "spotify-123",
    title: "Good One",
    authorName: "Vulture",
    websiteUrl: "https://example.com/good-one",
    feedUrl: "https://example.com/good-one.xml",
    lastSyncedAt: new Date("2026-05-01T12:00:00.000Z"),
};

const podcastDependencies = [
    { key: "episodes", label: "Episodes", count: 8 },
    {
        key: "episodeAppearances",
        label: "Episode appearances",
        count: 9,
    },
    {
        key: "episodeAppearanceReviews",
        label: "Episode appearance reviews",
        count: 10,
    },
    {
        key: "comedianPodcasts",
        label: "Comedian podcast links",
        count: 11,
    },
    {
        key: "candidateReviews",
        label: "Podcast candidate reviews retained with podcast cleared",
        count: 12,
    },
];

const podcastConfirmation = {
    entityType: "podcast",
    entityId: 77,
    label: "Good One",
    dependencies: podcastDependencies,
};

function makeRequest(method: "POST" | "DELETE", body: unknown) {
    return new NextRequest("http://localhost/api/admin/delete", {
        method,
        headers: { "Content-Type": "application/json" },
        body: typeof body === "string" ? body : JSON.stringify(body),
    });
}

function buildTx(overrides: Record<string, unknown> = {}) {
    return {
        club: {
            findUnique: vi.fn().mockResolvedValue(club),
            delete: vi.fn().mockResolvedValue(club),
        },
        show: {
            count: vi.fn().mockResolvedValue(2),
            findUnique: vi.fn(),
            delete: vi.fn(),
        },
        ticket: { count: vi.fn().mockResolvedValue(3) },
        lineupItem: { count: vi.fn().mockResolvedValue(4) },
        taggedShow: { count: vi.fn().mockResolvedValue(5) },
        sentNotification: { count: vi.fn().mockResolvedValue(6) },
        scrapingSource: { count: vi.fn().mockResolvedValue(1) },
        taggedClub: { count: vi.fn().mockResolvedValue(0) },
        emailSubscription: { count: vi.fn().mockResolvedValue(0) },
        processedEmail: { count: vi.fn().mockResolvedValue(0) },
        productionCompanyVenue: { count: vi.fn().mockResolvedValue(0) },
        clubAlias: { count: vi.fn().mockResolvedValue(0) },
        comedian: {
            count: vi.fn().mockResolvedValue(0),
            findUnique: vi.fn(),
            delete: vi.fn(),
        },
        favoriteComedian: { count: vi.fn().mockResolvedValue(0) },
        taggedComedian: { count: vi.fn().mockResolvedValue(0) },
        comedianPodcastAppearance: { count: vi.fn().mockResolvedValue(0) },
        comedianPodcastIdentityLink: { count: vi.fn().mockResolvedValue(0) },
        comedianPodcast: { count: vi.fn().mockResolvedValue(0) },
        podcastCandidateReview: { count: vi.fn().mockResolvedValue(0) },
        podcast: {
            findUnique: vi.fn().mockResolvedValue(podcast),
            delete: vi.fn().mockResolvedValue(podcast),
        },
        podcastEpisode: { count: vi.fn().mockResolvedValue(8) },
        episodeAppearance: { count: vi.fn().mockResolvedValue(0) },
        episodeAppearanceReview: { count: vi.fn().mockResolvedValue(0) },
        adminActionAudit: { create: vi.fn().mockResolvedValue({ id: 123 }) },
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.mockResolvedValue(adminSession as never);
    mockFindUserProfile.mockResolvedValue({
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    } as never);
    mockTransaction.mockImplementation(async (callback) =>
        callback(buildTx() as never),
    );
});

describe("POST /api/admin/delete", () => {
    it("returns 401 when auth() returns null", async () => {
        mockAuth.mockResolvedValue(null as never);

        const res = await POST(
            makeRequest("POST", { entityType: "club", entityId: 42 }),
        );

        expect(res.status).toBe(401);
    });

    it("returns 422 when session has no profile", async () => {
        mockAuth.mockResolvedValue({ user: {} } as never);

        const res = await POST(
            makeRequest("POST", { entityType: "club", entityId: 42 }),
        );

        expect(res.status).toBe(422);
    });

    it("returns 403 when profile.role is not admin", async () => {
        mockAuth.mockResolvedValue({
            profile: { id: "profile-1", userid: "user-1", role: "user" },
        } as never);
        mockFindUserProfile.mockResolvedValue({
            id: "profile-1",
            userid: "user-1",
            role: "user",
        } as never);

        const res = await POST(
            makeRequest("POST", { entityType: "club", entityId: 42 }),
        );

        expect(res.status).toBe(403);
    });

    it("rejects arbitrary entity types instead of accepting browser-supplied table names", async () => {
        const res = await POST(
            makeRequest("POST", {
                entityType: "admin_action_audits",
                entityId: 42,
            }),
        );

        expect(res.status).toBe(400);
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("returns dependency counts and the exact confirmation payload for a typed entity", async () => {
        const res = await POST(
            makeRequest("POST", { entityType: "club", entityId: 42 }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.preview).toMatchObject({
            entityType: "club",
            entityId: 42,
            label: "Gotham Comedy Club",
            confirmation: clubConfirmation,
        });
        expect(body.preview.dependencies).toEqual(clubDependencies);
    });

    it("returns podcast dependency counts and confirmation payloads", async () => {
        const tx = buildTx({
            episodeAppearance: { count: vi.fn().mockResolvedValue(9) },
            episodeAppearanceReview: { count: vi.fn().mockResolvedValue(10) },
            comedianPodcast: { count: vi.fn().mockResolvedValue(11) },
            podcastCandidateReview: { count: vi.fn().mockResolvedValue(12) },
        });
        mockTransaction.mockImplementation(async (callback) =>
            callback(tx as never),
        );

        const res = await POST(
            makeRequest("POST", { entityType: "podcast", entityId: 77 }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.preview).toMatchObject({
            entityType: "podcast",
            entityId: 77,
            label: "Good One",
            confirmation: podcastConfirmation,
        });
        expect(body.preview.dependencies).toEqual(podcastDependencies);
        expect(tx.podcast.findUnique).toHaveBeenCalledWith({
            where: { id: 77 },
            select: {
                id: true,
                slug: true,
                source: true,
                sourcePodcastId: true,
                title: true,
                authorName: true,
                websiteUrl: true,
                feedUrl: true,
                lastSyncedAt: true,
            },
        });
    });
});

describe("DELETE /api/admin/delete", () => {
    it("returns 401 when auth() returns null", async () => {
        mockAuth.mockResolvedValue(null as never);

        const res = await DELETE(
            makeRequest("DELETE", {
                entityType: "club",
                entityId: 42,
                reason: "duplicate venue cleanup",
                confirmation: clubConfirmation,
            }),
        );

        expect(res.status).toBe(401);
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("requires a reason before deleting", async () => {
        const res = await DELETE(
            makeRequest("DELETE", {
                entityType: "club",
                entityId: 42,
                reason: "",
                confirmation: {
                    entityType: "club",
                    entityId: 42,
                    label: "Gotham Comedy Club",
                    dependencies: clubDependencies,
                },
            }),
        );

        expect(res.status).toBe(400);
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("refuses a mismatched confirmation payload and does not delete", async () => {
        const tx = buildTx();
        mockTransaction.mockImplementation(async (callback) =>
            callback(tx as never),
        );

        const res = await DELETE(
            makeRequest("DELETE", {
                entityType: "club",
                entityId: 42,
                reason: "duplicate venue cleanup",
                confirmation: {
                    entityType: "club",
                    entityId: 42,
                    label: "Wrong Club",
                    dependencies: clubDependencies,
                },
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.expectedConfirmation).toEqual({
            entityType: "club",
            entityId: 42,
            label: "Gotham Comedy Club",
            dependencies: clubDependencies,
        });
        expect(tx.adminActionAudit.create).not.toHaveBeenCalled();
        expect(tx.club.delete).not.toHaveBeenCalled();
    });

    it("refuses confirmation when dependency counts have changed", async () => {
        const tx = buildTx();
        mockTransaction.mockImplementation(async (callback) =>
            callback(tx as never),
        );

        const res = await DELETE(
            makeRequest("DELETE", {
                entityType: "club",
                entityId: 42,
                reason: "duplicate venue cleanup",
                confirmation: {
                    ...clubConfirmation,
                    dependencies: [{ key: "shows", label: "Shows", count: 1 }],
                },
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.expectedConfirmation.dependencies).toEqual(
            clubDependencies,
        );
        expect(tx.adminActionAudit.create).not.toHaveBeenCalled();
        expect(tx.club.delete).not.toHaveBeenCalled();
    });

    it("writes an audit row with reason and dependency context before deleting", async () => {
        const events: string[] = [];
        const tx = buildTx({
            adminActionAudit: {
                create: vi.fn().mockImplementation(async () => {
                    events.push("audit");
                    return { id: 123 };
                }),
            },
            club: {
                findUnique: vi.fn().mockResolvedValue(club),
                delete: vi.fn().mockImplementation(async () => {
                    events.push("delete");
                    return club;
                }),
            },
        });
        mockTransaction.mockImplementation(async (callback) =>
            callback(tx as never),
        );

        const res = await DELETE(
            makeRequest("DELETE", {
                entityType: "club",
                entityId: 42,
                reason: "duplicate venue cleanup",
                confirmation: clubConfirmation,
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.deleted).toMatchObject({
            entityType: "club",
            entityId: 42,
            label: "Gotham Comedy Club",
        });
        expect(events).toEqual(["audit", "delete"]);
        expect(tx.adminActionAudit.create).toHaveBeenCalledWith({
            data: expect.objectContaining({
                actorProfileId: "profile-1",
                action: "club.delete",
                entityType: "club",
                entityId: "42",
                reason: "duplicate venue cleanup",
                before: expect.objectContaining({
                    entity: club,
                    dependencies: expect.arrayContaining([
                        { key: "shows", label: "Shows", count: 2 },
                        { key: "tickets", label: "Tickets", count: 3 },
                    ]),
                }),
                after: { deleted: true },
            }),
        });
        expect(tx.club.delete).toHaveBeenCalledWith({ where: { id: 42 } });
        expect(mockRevalidateTag).toHaveBeenCalledWith("club-detail-data");
        expect(mockRevalidateTag).toHaveBeenCalledWith("club-metadata");
        expect(mockRevalidateTag).toHaveBeenCalledWith("Gotham Comedy Club");
    });

    it("writes podcast delete audit context and deletes through the podcast workflow", async () => {
        const events: string[] = [];
        const tx = buildTx({
            episodeAppearance: { count: vi.fn().mockResolvedValue(9) },
            episodeAppearanceReview: { count: vi.fn().mockResolvedValue(10) },
            comedianPodcast: { count: vi.fn().mockResolvedValue(11) },
            podcastCandidateReview: { count: vi.fn().mockResolvedValue(12) },
            adminActionAudit: {
                create: vi.fn().mockImplementation(async () => {
                    events.push("audit");
                    return { id: 456 };
                }),
            },
            podcast: {
                findUnique: vi.fn().mockResolvedValue(podcast),
                delete: vi.fn().mockImplementation(async () => {
                    events.push("delete");
                    return podcast;
                }),
            },
        });
        mockTransaction.mockImplementation(async (callback) =>
            callback(tx as never),
        );

        const res = await DELETE(
            makeRequest("DELETE", {
                entityType: "podcast",
                entityId: 77,
                reason: "duplicate podcast cleanup",
                confirmation: podcastConfirmation,
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.deleted).toMatchObject({
            entityType: "podcast",
            entityId: 77,
            label: "Good One",
        });
        expect(events).toEqual(["audit", "delete"]);
        expect(tx.adminActionAudit.create).toHaveBeenCalledWith({
            data: expect.objectContaining({
                actorProfileId: "profile-1",
                action: "podcast.delete",
                entityType: "podcast",
                entityId: "77",
                reason: "duplicate podcast cleanup",
                before: expect.objectContaining({
                    entity: expect.objectContaining({
                        id: 77,
                        slug: "good-one",
                        title: "Good One",
                        lastSyncedAt: "2026-05-01T12:00:00.000Z",
                    }),
                    dependencies: podcastDependencies,
                }),
                after: { deleted: true },
            }),
        });
        expect(tx.podcast.delete).toHaveBeenCalledWith({ where: { id: 77 } });
        expect(mockRevalidateTag).toHaveBeenCalledWith("podcast-detail-data");
        expect(mockRevalidateTag).toHaveBeenCalledWith("podcast-metadata");
        expect(mockRevalidateTag).toHaveBeenCalledWith("Good One");
    });
});
