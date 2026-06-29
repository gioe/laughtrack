import { describe, expect, it, vi } from "vitest";

import { renewYouTubeWebSubSubscriptions } from "./youtubeWebSubSubscriptions";

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
});
