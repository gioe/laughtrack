import { describe, expect, it, vi } from "vitest";

import {
    buildYouTubeFeedTopicUrl,
    resolveYouTubeWebSubCallbackUrl,
    syncYouTubeWebSubSubscriptions,
    DEFAULT_REQUESTED_LEASE_SECONDS,
    type YouTubeWebSubWorkerDbClient,
    type SubscriptionUpsertArgs,
    type SubscriptionUpdateArgs,
} from "./youtubeWebSubSubscriptions";

type FetchFn = (input: string, init?: RequestInit) => Promise<Response>;

const NOW = new Date("2026-06-30T00:00:00.000Z");
const CALLBACK_URL = "https://laugh-track.com/api/webhooks/youtube";

interface DbFixture {
    feedIngestionEnabled?: boolean | null;
    comedians?: Array<{
        uuid: string;
        name: string;
        youtubeChannelId: string | null;
    }>;
    subscriptions?: Array<{
        id: number;
        comedianId: string;
        youtubeChannelId: string;
        status: string;
        leaseExpiresAt: Date | null;
    }>;
}

function makeDbClient(fixture: DbFixture) {
    const enabled =
        fixture.feedIngestionEnabled === undefined ||
        fixture.feedIngestionEnabled === null
            ? null
            : { feedIngestionEnabled: fixture.feedIngestionEnabled };

    const findSettingFirst = vi.fn(async () => enabled);
    const findComedians = vi.fn(async () => fixture.comedians ?? []);
    const findSubscriptions = vi.fn(async () => fixture.subscriptions ?? []);
    const upsert = vi.fn(
        async (_args: SubscriptionUpsertArgs): Promise<unknown> => ({}),
    );
    const update = vi.fn(
        async (_args: SubscriptionUpdateArgs): Promise<unknown> => ({}),
    );

    const dbClient: YouTubeWebSubWorkerDbClient = {
        youTubeWebSubSetting: { findFirst: findSettingFirst },
        comedian: { findMany: findComedians },
        youTubeWebSubSubscription: {
            findMany: findSubscriptions,
            upsert,
            update,
        },
    };

    return { dbClient, findComedians, findSubscriptions, upsert, update };
}

function okFetch(status = 202): ReturnType<typeof vi.fn<FetchFn>> {
    return vi.fn(async () => new Response("", { status }));
}

describe("syncYouTubeWebSubSubscriptions gating", () => {
    it("does nothing and reports gated when global feed ingestion is disabled", async () => {
        const { dbClient, findComedians, upsert } = makeDbClient({
            feedIngestionEnabled: false,
            comedians: [
                { uuid: "c1", name: "Jane", youtubeChannelId: "UC-1" },
            ],
        });
        const fetchFn = okFetch();

        const result = await syncYouTubeWebSubSubscriptions({
            dbClient,
            fetchFn,
            callbackUrl: CALLBACK_URL,
            now: NOW,
        });

        expect(result.gated).toBe(true);
        expect(result.total).toBe(0);
        expect(findComedians).not.toHaveBeenCalled();
        expect(fetchFn).not.toHaveBeenCalled();
        expect(upsert).not.toHaveBeenCalled();
    });

    it("treats a missing settings row as disabled", async () => {
        const { dbClient, findComedians } = makeDbClient({
            feedIngestionEnabled: null,
        });
        const fetchFn = okFetch();

        const result = await syncYouTubeWebSubSubscriptions({
            dbClient,
            fetchFn,
            callbackUrl: CALLBACK_URL,
            now: NOW,
        });

        expect(result.gated).toBe(true);
        expect(findComedians).not.toHaveBeenCalled();
        expect(fetchFn).not.toHaveBeenCalled();
    });

    it("queries only comedians with a channel ID and the feed flag enabled", async () => {
        const { dbClient, findComedians } = makeDbClient({
            feedIngestionEnabled: true,
            comedians: [],
        });

        await syncYouTubeWebSubSubscriptions({
            dbClient,
            fetchFn: okFetch(),
            callbackUrl: CALLBACK_URL,
            now: NOW,
        });

        expect(findComedians).toHaveBeenCalledWith({
            where: {
                youtubeChannelId: { not: null },
                youtubeLiveFeedEnabled: true,
            },
            select: { uuid: true, name: true, youtubeChannelId: true },
            orderBy: { id: "asc" },
        });
    });
});

describe("syncYouTubeWebSubSubscriptions subscribe/persist", () => {
    it("subscribes a new eligible comedian and persists lease + attempt state", async () => {
        const { dbClient, upsert } = makeDbClient({
            feedIngestionEnabled: true,
            comedians: [
                { uuid: "c1", name: "Jane Comic", youtubeChannelId: "UC-1" },
            ],
            subscriptions: [],
        });
        const fetchFn = okFetch(202);

        const result = await syncYouTubeWebSubSubscriptions({
            dbClient,
            fetchFn,
            callbackUrl: CALLBACK_URL,
            now: NOW,
        });

        expect(fetchFn).toHaveBeenCalledTimes(1);
        const body = new URLSearchParams(
            fetchFn.mock.calls[0][1]?.body as string,
        );
        expect(body.get("hub.mode")).toBe("subscribe");
        expect(body.get("hub.topic")).toBe(
            "https://www.youtube.com/feeds/videos.xml?channel_id=UC-1",
        );
        expect(body.get("hub.lease_seconds")).toBe(
            String(DEFAULT_REQUESTED_LEASE_SECONDS),
        );

        expect(upsert).toHaveBeenCalledTimes(1);
        const upsertArgs = upsert.mock.calls[0][0];
        expect(upsertArgs.where).toEqual({ youtubeChannelId: "UC-1" });
        expect(upsertArgs.create).toMatchObject({
            comedianId: "c1",
            youtubeChannelId: "UC-1",
            topicUrl:
                "https://www.youtube.com/feeds/videos.xml?channel_id=UC-1",
            status: "subscribed",
            leaseSeconds: DEFAULT_REQUESTED_LEASE_SECONDS,
            leaseExpiresAt: new Date("2026-07-05T00:00:00.000Z"),
            subscribedAt: NOW,
            lastSubscribeAttemptAt: NOW,
            lastSubscribeStatusCode: 202,
            lastSubscribeError: null,
        });

        expect(result).toMatchObject({
            gated: false,
            dryRun: false,
            total: 1,
            succeeded: 1,
            failed: 0,
            counts: { subscribe: 1, renew: 0, unsubscribe: 0, skip: 0 },
        });
    });

    it("records the failure reason and does not advance the lease on a non-ok hub response", async () => {
        const { dbClient, upsert } = makeDbClient({
            feedIngestionEnabled: true,
            comedians: [
                { uuid: "c1", name: "Jane Comic", youtubeChannelId: "UC-1" },
            ],
            subscriptions: [],
        });
        const fetchFn = vi.fn(async () => new Response("no", { status: 500 }));
        const warn = vi.fn();

        const result = await syncYouTubeWebSubSubscriptions({
            dbClient,
            fetchFn,
            callbackUrl: CALLBACK_URL,
            logger: { warn },
            now: NOW,
        });

        const upsertArgs = upsert.mock.calls[0][0];
        expect(upsertArgs.create).toMatchObject({
            status: "failed",
            lastSubscribeStatusCode: 500,
            lastSubscribeError: "hub returned status 500",
        });
        expect(upsertArgs.create).not.toHaveProperty("leaseExpiresAt");
        expect(warn).toHaveBeenCalledWith(
            "[youtube-websub-worker] subscribe failed channel UC-1: hub returned status 500",
        );
        expect(result.failed).toBe(1);
        expect(result.succeeded).toBe(0);
    });

    it("continues persisting later channels when one hub request throws", async () => {
        const { dbClient, upsert } = makeDbClient({
            feedIngestionEnabled: true,
            comedians: [
                { uuid: "c1", name: "Jane", youtubeChannelId: "UC-1" },
                { uuid: "c2", name: "Sam", youtubeChannelId: "UC-2" },
            ],
            subscriptions: [],
        });
        const fetchFn = vi
            .fn<FetchFn>()
            .mockRejectedValueOnce(new Error("hub timeout"))
            .mockResolvedValueOnce(new Response("", { status: 202 }));
        const warn = vi.fn();

        const result = await syncYouTubeWebSubSubscriptions({
            dbClient,
            fetchFn,
            callbackUrl: CALLBACK_URL,
            logger: { warn },
            now: NOW,
        });

        expect(fetchFn).toHaveBeenCalledTimes(2);
        expect(upsert).toHaveBeenCalledTimes(2);
        expect(upsert.mock.calls[0][0].create).toMatchObject({
            status: "failed",
            lastSubscribeError: "hub timeout",
            lastSubscribeStatusCode: null,
        });
        expect(upsert.mock.calls[1][0].create).toMatchObject({
            status: "subscribed",
        });
        expect(result).toMatchObject({ succeeded: 1, failed: 1 });
    });
});

describe("syncYouTubeWebSubSubscriptions renew/skip/unsubscribe", () => {
    it("renews subscriptions expiring within the window and skips still-valid leases", async () => {
        const { dbClient, upsert } = makeDbClient({
            feedIngestionEnabled: true,
            comedians: [
                { uuid: "c1", name: "Expiring", youtubeChannelId: "UC-exp" },
                { uuid: "c2", name: "Fresh", youtubeChannelId: "UC-fresh" },
            ],
            subscriptions: [
                {
                    id: 10,
                    comedianId: "c1",
                    youtubeChannelId: "UC-exp",
                    status: "subscribed",
                    // expires in 12h — inside the 1-day renew window
                    leaseExpiresAt: new Date("2026-06-30T12:00:00.000Z"),
                },
                {
                    id: 11,
                    comedianId: "c2",
                    youtubeChannelId: "UC-fresh",
                    status: "subscribed",
                    // expires in 4 days — outside the renew window
                    leaseExpiresAt: new Date("2026-07-04T00:00:00.000Z"),
                },
            ],
        });
        const fetchFn = okFetch(202);

        const result = await syncYouTubeWebSubSubscriptions({
            dbClient,
            fetchFn,
            callbackUrl: CALLBACK_URL,
            now: NOW,
        });

        expect(fetchFn).toHaveBeenCalledTimes(1);
        expect(result.counts).toEqual({
            subscribe: 0,
            renew: 1,
            unsubscribe: 0,
            skip: 1,
        });
        // only the expiring one is re-subscribed/persisted
        expect(upsert).toHaveBeenCalledTimes(1);
        expect(upsert.mock.calls[0][0].where).toEqual({
            youtubeChannelId: "UC-exp",
        });
        expect(result.results).toEqual([
            expect.objectContaining({ action: "renew", ok: true }),
        ]);
    });

    it("unsubscribes active subscriptions whose comedian is no longer eligible and leaves failed orphans alone", async () => {
        const { dbClient, update, upsert } = makeDbClient({
            feedIngestionEnabled: true,
            comedians: [], // nobody eligible anymore (disabled / channel removed)
            subscriptions: [
                {
                    id: 20,
                    comedianId: "c1",
                    youtubeChannelId: "UC-gone",
                    status: "subscribed",
                    leaseExpiresAt: new Date("2026-07-04T00:00:00.000Z"),
                },
                {
                    id: 21,
                    comedianId: "c2",
                    youtubeChannelId: "UC-neverworked",
                    status: "failed",
                    leaseExpiresAt: null,
                },
            ],
        });
        const fetchFn = okFetch(202);

        const result = await syncYouTubeWebSubSubscriptions({
            dbClient,
            fetchFn,
            callbackUrl: CALLBACK_URL,
            now: NOW,
        });

        expect(result.counts).toEqual({
            subscribe: 0,
            renew: 0,
            unsubscribe: 1,
            skip: 0,
        });
        // unsubscribe hits the hub with mode=unsubscribe and updates by id
        const body = new URLSearchParams(
            fetchFn.mock.calls[0][1]?.body as string,
        );
        expect(body.get("hub.mode")).toBe("unsubscribe");
        expect(body.has("hub.lease_seconds")).toBe(false);
        expect(update).toHaveBeenCalledTimes(1);
        expect(update.mock.calls[0][0]).toMatchObject({
            where: { id: 20 },
            data: expect.objectContaining({
                status: "unsubscribed",
                unsubscribedAt: NOW,
            }),
        });
        // the failed orphan is never touched
        expect(upsert).not.toHaveBeenCalled();
    });

    it("does not flip status to unsubscribed when the hub rejects the teardown", async () => {
        const { dbClient, update } = makeDbClient({
            feedIngestionEnabled: true,
            comedians: [],
            subscriptions: [
                {
                    id: 30,
                    comedianId: "c1",
                    youtubeChannelId: "UC-gone",
                    status: "subscribed",
                    leaseExpiresAt: null,
                },
            ],
        });
        const fetchFn = vi.fn(async () => new Response("no", { status: 503 }));

        const result = await syncYouTubeWebSubSubscriptions({
            dbClient,
            fetchFn,
            callbackUrl: CALLBACK_URL,
            now: NOW,
            logger: { warn: vi.fn() },
        });

        const data = update.mock.calls[0][0].data;
        expect(data).not.toHaveProperty("status");
        expect(data).toMatchObject({
            lastSubscribeStatusCode: 503,
            lastSubscribeError: "hub returned status 503",
        });
        expect(result.failed).toBe(1);
    });
});

describe("syncYouTubeWebSubSubscriptions dry-run", () => {
    it("reports the intended subscribe/renew/unsubscribe plan with no network or db writes", async () => {
        const { dbClient, upsert, update } = makeDbClient({
            feedIngestionEnabled: true,
            comedians: [
                { uuid: "c1", name: "New", youtubeChannelId: "UC-new" },
                { uuid: "c2", name: "Expiring", youtubeChannelId: "UC-exp" },
            ],
            subscriptions: [
                {
                    id: 40,
                    comedianId: "c2",
                    youtubeChannelId: "UC-exp",
                    status: "subscribed",
                    leaseExpiresAt: new Date("2026-06-30T01:00:00.000Z"),
                },
                {
                    id: 41,
                    comedianId: "c3",
                    youtubeChannelId: "UC-orphan",
                    status: "subscribed",
                    leaseExpiresAt: null,
                },
            ],
        });
        const fetchFn = okFetch();

        const result = await syncYouTubeWebSubSubscriptions({
            dbClient,
            fetchFn,
            callbackUrl: CALLBACK_URL,
            now: NOW,
            dryRun: true,
        });

        expect(fetchFn).not.toHaveBeenCalled();
        expect(upsert).not.toHaveBeenCalled();
        expect(update).not.toHaveBeenCalled();
        expect(result.dryRun).toBe(true);
        expect(result.counts).toEqual({
            subscribe: 1,
            renew: 1,
            unsubscribe: 1,
            skip: 0,
        });
        expect(result.results).toEqual([
            expect.objectContaining({
                action: "subscribe",
                youtubeChannelId: "UC-new",
                ok: null,
                status: null,
            }),
            expect.objectContaining({
                action: "renew",
                youtubeChannelId: "UC-exp",
                ok: null,
            }),
            expect.objectContaining({
                action: "unsubscribe",
                youtubeChannelId: "UC-orphan",
                ok: null,
            }),
        ]);
    });
});

describe("youtube websub url helpers", () => {
    it("resolves the configured public callback URL and YouTube feed topic URL", () => {
        expect(
            resolveYouTubeWebSubCallbackUrl({
                YOUTUBE_WEBSUB_CALLBACK_URL:
                    "https://hooks.laugh-track.com/youtube",
                NEXT_PUBLIC_WEBSITE_URL: "https://laugh-track.com",
            }),
        ).toBe("https://hooks.laugh-track.com/youtube");
        expect(
            resolveYouTubeWebSubCallbackUrl({
                NEXT_PUBLIC_WEBSITE_URL: "https://laugh-track.com/",
            }),
        ).toBe("https://laugh-track.com/api/webhooks/youtube");
        expect(buildYouTubeFeedTopicUrl("UC-one/two")).toBe(
            "https://www.youtube.com/feeds/videos.xml?channel_id=UC-one%2Ftwo",
        );
    });
});
