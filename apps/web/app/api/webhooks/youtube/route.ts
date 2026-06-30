import { timingSafeEqual } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { withRequestMetrics } from "@/lib/metrics";
import { parseYouTubeWebSubFeed } from "@/lib/youtube/youtubeWebSub";
import { buildYouTubeFeedTopicUrl } from "@/lib/youtube/youtubeWebSubSubscriptions";

const YOUTUBE_FEED_ORIGIN = "https://www.youtube.com";
const YOUTUBE_FEED_PATHS = new Set([
    "/feeds/videos.xml",
    "/xml/feeds/videos.xml",
]);

export const GET = withRequestMetrics(async function GET(req: NextRequest) {
    if (!hasValidCallbackSecret(req)) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const challenge = req.nextUrl.searchParams.get("hub.challenge");
    const mode = req.nextUrl.searchParams.get("hub.mode");
    const topic = req.nextUrl.searchParams.get("hub.topic");

    if (
        !challenge ||
        !isSupportedHubMode(mode) ||
        !topic ||
        !isYouTubeFeedTopic(topic)
    ) {
        return NextResponse.json(
            { error: "invalid_verification_request" },
            { status: 400 },
        );
    }

    return new NextResponse(challenge, {
        status: 200,
        headers: { "content-type": "text/plain; charset=utf-8" },
    });
});

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    if (!hasValidCallbackSecret(req)) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const payloadXml = await req.text();
    const topicUrl = normalizeTopicUrl(
        req.nextUrl.searchParams.get("hub.topic"),
    );

    if (!looksLikeCompleteXml(payloadXml)) {
        await db.youTubeWebSubEvent.create({
            data: {
                topicUrl,
                eventStatus: "failed",
                failureReason: "malformed_xml",
                payloadXml,
                payloadJson: {
                    error: "malformed_xml",
                },
            },
        });

        return NextResponse.json(
            { ok: false, stored: 1, error: "malformed_xml" },
            { status: 202 },
        );
    }

    const entries = parseYouTubeWebSubFeed(payloadXml);

    if (entries.length === 0) {
        await db.youTubeWebSubEvent.create({
            data: {
                topicUrl,
                eventStatus: "received",
                payloadXml,
                payloadJson: {
                    entries: [],
                },
            },
        });

        return NextResponse.json({ ok: true, stored: 1 }, { status: 202 });
    }

    let stored = 0;
    for (const entry of entries) {
        const comedian = entry.channelId
            ? await db.comedian.findFirst({
                  where: { youtubeChannelId: entry.channelId },
                  select: { uuid: true },
              })
            : null;

        await db.youTubeWebSubEvent.create({
            data: {
                comedianId: comedian?.uuid,
                youtubeChannelId: entry.channelId,
                youtubeVideoId: entry.videoId,
                videoTitle: entry.title,
                videoUrl: entry.link,
                topicUrl: topicUrl ?? buildTopicUrl(entry.channelId),
                eventStatus: "received",
                publishedAt: parseDate(entry.publishedAt),
                feedUpdatedAt: parseDate(entry.updatedAt),
                payloadXml,
                payloadJson: {
                    entry: {
                        videoId: entry.videoId,
                        channelId: entry.channelId,
                        title: entry.title,
                        link: entry.link,
                        publishedAt: entry.publishedAt,
                        updatedAt: entry.updatedAt,
                    },
                },
            },
        });
        stored += 1;
    }

    return NextResponse.json({ ok: true, stored }, { status: 202 });
});

function hasValidCallbackSecret(req: NextRequest): boolean {
    const expected = process.env.YOUTUBE_WEBSUB_CALLBACK_SECRET;
    const supplied =
        req.nextUrl.searchParams.get("secret") ??
        req.nextUrl.searchParams.get("hub.verify_token");

    if (!expected || !supplied) {
        return false;
    }

    const suppliedBuf = Buffer.from(supplied);
    const expectedBuf = Buffer.from(expected);

    return (
        suppliedBuf.length === expectedBuf.length &&
        timingSafeEqual(suppliedBuf, expectedBuf)
    );
}

function isSupportedHubMode(mode: string | null): boolean {
    return mode === "subscribe" || mode === "unsubscribe";
}

function isYouTubeFeedTopic(topic: string): boolean {
    try {
        const url = new URL(topic);
        return (
            url.origin === YOUTUBE_FEED_ORIGIN &&
            YOUTUBE_FEED_PATHS.has(url.pathname) &&
            Boolean(url.searchParams.get("channel_id"))
        );
    } catch {
        return false;
    }
}

function normalizeTopicUrl(topic: string | null): string | null {
    return topic && isYouTubeFeedTopic(topic) ? topic : null;
}

function buildTopicUrl(channelId: string | null): string | null {
    return channelId ? buildYouTubeFeedTopicUrl(channelId) : null;
}

function parseDate(value: string | null): Date | null {
    if (!value) {
        return null;
    }

    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
}

function looksLikeCompleteXml(xml: string): boolean {
    const trimmed = xml.trim();
    if (!trimmed) {
        return false;
    }

    const withoutDeclaration = trimmed.replace(/^<\?xml\b[\s\S]*?\?>\s*/i, "");
    const rootMatch = /^<([a-zA-Z_][\w:.-]*)\b[\s\S]*<\/\1>\s*$/.exec(
        withoutDeclaration,
    );
    if (!rootMatch) {
        return false;
    }

    return (
        countMatches(withoutDeclaration, /<entry\b/gi) ===
        countMatches(withoutDeclaration, /<\/entry>/gi)
    );
}

function countMatches(value: string, pattern: RegExp): number {
    return Array.from(value.matchAll(pattern)).length;
}
