import { describe, expect, it, vi } from "vitest";

import {
    buildYouTubeChannelLookup,
    resolveYouTubeChannelId,
    resolveYouTubeChannelIdFromHtml,
} from "./youtubeChannelResolver";

const CHANNEL_ID = "UCGmMFJB36GBXTgaLtfGd6Jg";

function htmlResponse(body: string, init?: ResponseInit): Response {
    return new Response(body, {
        status: 200,
        headers: { "content-type": "text/html" },
        ...init,
    });
}

describe("youtubeChannelResolver", () => {
    it("treats canonical channel URLs and IDs as direct channel ID lookups", () => {
        expect(buildYouTubeChannelLookup(CHANNEL_ID)).toEqual({
            kind: "channel_id",
            channelId: CHANNEL_ID,
        });
        expect(
            buildYouTubeChannelLookup(
                `https://www.youtube.com/channel/${CHANNEL_ID}`,
            ),
        ).toEqual({
            kind: "channel_id",
            channelId: CHANNEL_ID,
        });
    });

    it("normalizes handles and bare account names to YouTube handle URLs", () => {
        expect(buildYouTubeChannelLookup("@marknormand")).toEqual({
            kind: "url",
            url: "https://www.youtube.com/@marknormand",
        });
        expect(buildYouTubeChannelLookup("marknormand")).toEqual({
            kind: "url",
            url: "https://www.youtube.com/@marknormand",
        });
    });

    it("extracts the canonical channel ID from a YouTube channel page", async () => {
        const fetchFn = vi.fn(async () =>
            htmlResponse(
                `<html><head><link rel="canonical" href="https://www.youtube.com/channel/${CHANNEL_ID}"></head></html>`,
            ),
        );

        await expect(
            resolveYouTubeChannelId("marknormand", { fetchFn }),
        ).resolves.toEqual({
            status: "resolved",
            channelId: CHANNEL_ID,
            sourceUrl: "https://www.youtube.com/@marknormand",
        });

        expect(fetchFn).toHaveBeenCalledWith(
            "https://www.youtube.com/@marknormand",
            expect.objectContaining({
                headers: {
                    accept: "text/html,application/xhtml+xml",
                },
            }),
        );
    });

    it("falls back to channel metadata when canonical link is unavailable", () => {
        expect(
            resolveYouTubeChannelIdFromHtml(
                `<script>{"externalId":"${CHANNEL_ID}"}</script>`,
                "https://www.youtube.com/@marknormand",
            ),
        ).toEqual({
            status: "resolved",
            channelId: CHANNEL_ID,
            sourceUrl: "https://www.youtube.com/@marknormand",
        });
    });

    it("reports ambiguous pages instead of guessing", () => {
        expect(
            resolveYouTubeChannelIdFromHtml(
                `<script>{"channelId":"UCGmMFJB36GBXTgaLtfGd6Jg","externalId":"UCTrOYaMDI7QiPnRzwWdYK6Q"}</script>`,
                "https://www.youtube.com/@example",
            ),
        ).toEqual({
            status: "failed",
            reason: "ambiguous",
            sourceUrl: "https://www.youtube.com/@example",
            detail: "Found 2 channel IDs: UCGmMFJB36GBXTgaLtfGd6Jg, UCTrOYaMDI7QiPnRzwWdYK6Q",
        });
    });

    it("reports fetch failures with context", async () => {
        const fetchFn = vi.fn(async () =>
            htmlResponse("not found", { status: 404 }),
        );

        await expect(
            resolveYouTubeChannelId("@missing", { fetchFn }),
        ).resolves.toEqual({
            status: "failed",
            reason: "fetch_failed",
            sourceUrl: "https://www.youtube.com/@missing",
            detail: "YouTube returned status 404",
        });
    });
});
