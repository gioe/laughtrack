import { describe, expect, it, vi } from "vitest";

import {
    buildYouTubeFeedTopicUrl,
    renewYouTubeWebSubSubscriptions,
    resolveYouTubeWebSubCallbackUrl,
} from "./youtubeWebSubSubscriptions";

type FetchFn = (input: string, init?: RequestInit) => Promise<Response>;

describe("renewYouTubeWebSubSubscriptions", () => {
    it("posts subscribe requests for each comedian with a YouTube channel ID", async () => {
        const findMany = vi.fn(async () => [
            {
                uuid: "comedian-1",
                name: "Jane Comic",
                youtubeChannelId: "UC-one",
            },
            {
                uuid: "comedian-2",
                name: "Sam Comic",
                youtubeChannelId: "UC-two",
            },
        ]);
        const fetchFn: ReturnType<typeof vi.fn<FetchFn>> = vi.fn(
            async () => new Response("", { status: 202 }),
        );

        const result = await renewYouTubeWebSubSubscriptions({
            dbClient: {
                comedian: { findMany },
            },
            fetchFn,
            callbackUrl: "https://laugh-track.com/api/webhooks/youtube",
        });

        expect(findMany).toHaveBeenCalledWith({
            where: {
                youtubeChannelId: { not: null },
            },
            select: {
                uuid: true,
                name: true,
                youtubeChannelId: true,
            },
            orderBy: { id: "asc" },
        });
        expect(fetchFn).toHaveBeenCalledTimes(2);
        expect(fetchFn).toHaveBeenNthCalledWith(
            1,
            "https://pubsubhubbub.appspot.com/",
            expect.objectContaining({
                method: "POST",
                headers: {
                    "content-type": "application/x-www-form-urlencoded",
                },
            }),
        );
        expect(
            new URLSearchParams(fetchFn.mock.calls[0][1]?.body as string),
        ).toEqual(
            new URLSearchParams({
                "hub.mode": "subscribe",
                "hub.topic":
                    "https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC-one",
                "hub.callback": "https://laugh-track.com/api/webhooks/youtube",
                "hub.verify": "async",
            }),
        );
        expect(
            new URLSearchParams(fetchFn.mock.calls[1][1]?.body as string).get(
                "hub.topic",
            ),
        ).toBe(
            "https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC-two",
        );
        expect(result).toEqual({
            total: 2,
            succeeded: 2,
            failed: 0,
            results: [
                {
                    comedianId: "comedian-1",
                    comedianName: "Jane Comic",
                    youtubeChannelId: "UC-one",
                    ok: true,
                    status: 202,
                },
                {
                    comedianId: "comedian-2",
                    comedianName: "Sam Comic",
                    youtubeChannelId: "UC-two",
                    ok: true,
                    status: 202,
                },
            ],
        });
    });

    it("logs per-channel hub failures and continues renewing later channels", async () => {
        const findMany = vi.fn(async () => [
            {
                uuid: "comedian-1",
                name: "Jane Comic",
                youtubeChannelId: "UC-one",
            },
            {
                uuid: "comedian-2",
                name: "Sam Comic",
                youtubeChannelId: "UC-two",
            },
        ]);
        const fetchFn: ReturnType<typeof vi.fn<FetchFn>> = vi
            .fn<FetchFn>()
            .mockRejectedValueOnce(new Error("hub timeout"))
            .mockResolvedValueOnce(new Response("", { status: 202 }));
        const warn = vi.fn();

        const result = await renewYouTubeWebSubSubscriptions({
            dbClient: {
                comedian: { findMany },
            },
            fetchFn,
            callbackUrl: "https://laugh-track.com/api/webhooks/youtube",
            logger: { warn },
        });

        expect(fetchFn).toHaveBeenCalledTimes(2);
        expect(warn).toHaveBeenCalledWith(
            "[youtube-websub-renewal] failed channel UC-one for Jane Comic: hub timeout",
        );
        expect(result).toEqual({
            total: 2,
            succeeded: 1,
            failed: 1,
            results: [
                {
                    comedianId: "comedian-1",
                    comedianName: "Jane Comic",
                    youtubeChannelId: "UC-one",
                    ok: false,
                    status: null,
                    error: "hub timeout",
                },
                {
                    comedianId: "comedian-2",
                    comedianName: "Sam Comic",
                    youtubeChannelId: "UC-two",
                    ok: true,
                    status: 202,
                },
            ],
        });
    });

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
            "https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC-one%2Ftwo",
        );
    });
});
