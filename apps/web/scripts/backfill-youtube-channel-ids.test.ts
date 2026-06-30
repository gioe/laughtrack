import { describe, expect, it, vi } from "vitest";

import {
    backfillYouTubeChannelIds,
    parseArgs,
    summarizeBackfillResults,
} from "./backfill-youtube-channel-ids";

const CHANNEL_ID = "UCGmMFJB36GBXTgaLtfGd6Jg";

function htmlResponse(body: string, init?: ResponseInit): Response {
    return new Response(body, {
        status: 200,
        headers: { "content-type": "text/html" },
        ...init,
    });
}

function comedianRow(overrides: Record<string, unknown> = {}) {
    return {
        id: 1,
        uuid: "comedian-uuid",
        name: "Mark Normand",
        youtubeAccount: "marknormand",
        youtubeChannelId: null,
        ...overrides,
    };
}

describe("backfill-youtube-channel-ids", () => {
    it("plans updates in dry-run mode without writing to the database", async () => {
        const db = {
            comedian: {
                findMany: vi.fn(async () => [comedianRow()]),
                update: vi.fn(),
            },
        };
        const fetchFn = vi.fn(async () =>
            htmlResponse(
                `<link rel="canonical" href="https://www.youtube.com/channel/${CHANNEL_ID}">`,
            ),
        );

        const results = await backfillYouTubeChannelIds(db, {
            apply: false,
            overwrite: false,
            limit: null,
            fetchFn,
        });

        expect(db.comedian.update).not.toHaveBeenCalled();
        expect(results).toEqual([
            {
                status: "planned_update",
                comedian: {
                    id: 1,
                    uuid: "comedian-uuid",
                    name: "Mark Normand",
                },
                youtubeAccount: "marknormand",
                previousYoutubeChannelId: null,
                resolvedYoutubeChannelId: CHANNEL_ID,
                sourceUrl: "https://www.youtube.com/@marknormand",
            },
        ]);
        expect(
            summarizeBackfillResults(results, {
                apply: false,
                overwrite: false,
                limit: null,
            }),
        ).toMatchObject({
            mode: "dry-run",
            candidateCount: 1,
            plannedUpdateCount: 1,
            updatedCount: 0,
            nextStep:
                "Run bin/backfill-youtube-channel-ids --apply to persist planned youtubeChannelId updates.",
        });
    });

    it("updates resolved channel IDs in apply mode", async () => {
        const db = {
            comedian: {
                findMany: vi.fn(async () => [comedianRow()]),
                update: vi.fn(async () => ({})),
            },
        };
        const fetchFn = vi.fn(async () =>
            htmlResponse(
                `<link rel="canonical" href="https://www.youtube.com/channel/${CHANNEL_ID}">`,
            ),
        );

        const results = await backfillYouTubeChannelIds(db, {
            apply: true,
            overwrite: false,
            limit: 10,
            fetchFn,
        });

        expect(db.comedian.findMany).toHaveBeenCalledWith(
            expect.objectContaining({
                take: 10,
            }),
        );
        expect(db.comedian.update).toHaveBeenCalledWith({
            where: {
                id: 1,
            },
            data: {
                youtubeChannelId: CHANNEL_ID,
            },
        });
        expect(results[0]).toMatchObject({
            status: "updated",
            resolvedYoutubeChannelId: CHANNEL_ID,
        });
    });

    it("preserves existing channel IDs unless overwrite is enabled", async () => {
        const existingChannelId = "UCTrOYaMDI7QiPnRzwWdYK6Q";
        const db = {
            comedian: {
                findMany: vi.fn(async () => [
                    comedianRow({ youtubeChannelId: existingChannelId }),
                ]),
                update: vi.fn(),
            },
        };
        const fetchFn = vi.fn();

        await expect(
            backfillYouTubeChannelIds(db, {
                apply: true,
                overwrite: false,
                limit: null,
                fetchFn,
            }),
        ).resolves.toEqual([
            {
                status: "skipped_existing",
                comedian: {
                    id: 1,
                    uuid: "comedian-uuid",
                    name: "Mark Normand",
                },
                existingYoutubeChannelId: existingChannelId,
            },
        ]);

        expect(fetchFn).not.toHaveBeenCalled();
        expect(db.comedian.update).not.toHaveBeenCalled();
    });

    it("overwrites existing channel IDs only when requested", async () => {
        const db = {
            comedian: {
                findMany: vi.fn(async () => [
                    comedianRow({
                        youtubeChannelId: "UCTrOYaMDI7QiPnRzwWdYK6Q",
                    }),
                ]),
                update: vi.fn(async () => ({})),
            },
        };
        const fetchFn = vi.fn(async () =>
            htmlResponse(
                `<link rel="canonical" href="https://www.youtube.com/channel/${CHANNEL_ID}">`,
            ),
        );

        const results = await backfillYouTubeChannelIds(db, {
            apply: true,
            overwrite: true,
            limit: null,
            fetchFn,
        });

        expect(db.comedian.update).toHaveBeenCalledWith({
            where: {
                id: 1,
            },
            data: {
                youtubeChannelId: CHANNEL_ID,
            },
        });
        expect(results[0]).toMatchObject({
            status: "updated",
            previousYoutubeChannelId: "UCTrOYaMDI7QiPnRzwWdYK6Q",
            resolvedYoutubeChannelId: CHANNEL_ID,
        });
    });

    it("reports resolution failures with comedian identifiers", async () => {
        const db = {
            comedian: {
                findMany: vi.fn(async () => [comedianRow()]),
                update: vi.fn(),
            },
        };
        const fetchFn = vi.fn(async () =>
            htmlResponse("missing", { status: 404 }),
        );

        await expect(
            backfillYouTubeChannelIds(db, {
                apply: true,
                overwrite: false,
                limit: null,
                fetchFn,
            }),
        ).resolves.toEqual([
            {
                status: "failed",
                comedian: {
                    id: 1,
                    uuid: "comedian-uuid",
                    name: "Mark Normand",
                },
                youtubeAccount: "marknormand",
                reason: "fetch_failed",
                sourceUrl: "https://www.youtube.com/@marknormand",
                detail: "YouTube returned status 404",
            },
        ]);

        expect(db.comedian.update).not.toHaveBeenCalled();
    });

    it("parses apply, overwrite, and limit flags", () => {
        expect(parseArgs(["--apply", "--overwrite", "--limit", "25"])).toEqual({
            apply: true,
            overwrite: true,
            limit: 25,
        });
        expect(parseArgs(["--limit=5"])).toEqual({
            apply: false,
            overwrite: false,
            limit: 5,
        });
        expect(() => parseArgs(["--limit", "0"])).toThrow(
            "--limit requires a positive integer value",
        );
    });
});
