import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("next/cache", () => ({
    revalidateTag: vi.fn(),
}));

vi.mock("@/lib/db", () => {
    const txClient = {
        comedianPodcast: {
            findFirst: vi.fn(),
        },
        podcast: {
            update: vi.fn(),
        },
        adminActionAudit: {
            create: vi.fn(),
        },
    };
    return {
        db: {
            userProfile: {
                findFirst: vi.fn(),
            },
            $transaction: vi.fn(),
            __txClient: txClient,
        },
    };
});

import { auth } from "@/auth";
import { db } from "@/lib/db";
import { revalidateTag } from "next/cache";
import { PATCH } from "./route";

const mockAuth = vi.mocked(auth);
const mockFindUserProfile = vi.mocked(db.userProfile.findFirst);
const mockTransaction = vi.mocked(db.$transaction);
const mockRevalidateTag = vi.mocked(revalidateTag);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const txClient: any = (db as any).__txClient;
const mockFindLink = vi.mocked(txClient.comedianPodcast.findFirst);
const mockUpdatePodcast = vi.mocked(txClient.podcast.update);
const mockAuditCreate = vi.mocked(txClient.adminActionAudit.create);

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

function makeRequest(body: unknown) {
    return new NextRequest("http://localhost/api/admin/comedians/podcasts", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.mockResolvedValue(adminSession as never);
    mockFindUserProfile.mockResolvedValue({
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    } as never);
    mockFindLink.mockResolvedValue({
        id: 10,
        associationType: "host",
        source: "manual",
        reviewStatus: "accepted",
        confidence: 1,
        comedian: { id: 7, name: "Alex Example" },
        podcast: {
            id: 42,
            slug: "alex-podcast",
            title: "Alex Podcast",
            feedUrl: "https://old.example.com/rss.xml",
            websiteUrl: "https://pod.example.com",
        },
    });
    mockUpdatePodcast.mockImplementation(
        async (args: { data: { feedUrl: string | null } }) => ({
            id: 42,
            slug: "alex-podcast",
            title: "Alex Podcast",
            feedUrl: args.data.feedUrl,
            websiteUrl: "https://pod.example.com",
        }),
    );
    mockAuditCreate.mockResolvedValue({} as never);
    mockTransaction.mockImplementation(
        async (callback: (tx: typeof txClient) => unknown) =>
            callback(txClient),
    );
});

describe("PATCH /api/admin/comedians/podcasts", () => {
    it("requires admin access", async () => {
        mockAuth.mockResolvedValue(null as never);

        const res = await PATCH(
            makeRequest({
                comedianId: 7,
                podcastId: 42,
                feedUrl: "https://new.example.com/rss.xml",
            }),
        );

        expect(res.status).toBe(401);
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("updates a linked podcast RSS URL", async () => {
        const res = await PATCH(
            makeRequest({
                comedianId: 7,
                podcastId: 42,
                feedUrl: "https://new.example.com/rss.xml",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockUpdatePodcast).toHaveBeenCalledWith({
            where: { id: 42 },
            data: { feedUrl: "https://new.example.com/rss.xml" },
            select: {
                id: true,
                slug: true,
                title: true,
                feedUrl: true,
                websiteUrl: true,
            },
        });
        expect(body.podcast).toMatchObject({
            id: 42,
            title: "Alex Podcast",
            feedUrl: "https://new.example.com/rss.xml",
            associationType: "host",
        });
        expect(mockAuditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                action: "comedian_podcast.feed_url.update",
                entityType: "podcast",
                entityId: "42",
            }),
        });
        expect(mockRevalidateTag).toHaveBeenCalledWith("Alex Example");
        expect(mockRevalidateTag).toHaveBeenCalledWith("alex-podcast");
    });

    it("removes a linked podcast RSS URL", async () => {
        const res = await PATCH(
            makeRequest({
                comedianId: 7,
                podcastId: 42,
                feedUrl: null,
            }),
        );

        expect(res.status).toBe(200);
        expect(mockUpdatePodcast).toHaveBeenCalledWith(
            expect.objectContaining({
                data: { feedUrl: null },
            }),
        );
    });

    it("returns 404 when the podcast is not linked to the comedian", async () => {
        mockFindLink.mockResolvedValue(null);

        const res = await PATCH(
            makeRequest({
                comedianId: 7,
                podcastId: 42,
                feedUrl: "https://new.example.com/rss.xml",
            }),
        );

        expect(res.status).toBe(404);
        expect(mockUpdatePodcast).not.toHaveBeenCalled();
    });
});
