import { NextRequest, NextResponse } from "next/server";
import { withRequestMetrics } from "@/lib/metrics";
import { db } from "@/lib/db";
import { parseYouTubeWebSubFeed } from "@/lib/youtube/youtubeWebSub";

export const GET = withRequestMetrics(async function GET(req: NextRequest) {
    const challenge = req.nextUrl.searchParams.get("hub.challenge");
    const mode = req.nextUrl.searchParams.get("hub.mode");
    const topic = req.nextUrl.searchParams.get("hub.topic");

    if (!challenge || !mode || !topic) {
        return NextResponse.json({ error: "missing_challenge" }, { status: 400 });
    }

    return new NextResponse(challenge, {
        status: 200,
        headers: { "content-type": "text/plain; charset=utf-8" },
    });
});

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    const xml = await req.text();
    const entries = parseYouTubeWebSubFeed(xml).filter(
        (entry) => entry.videoId && entry.channelId,
    );

    let processed = 0;

    for (const entry of entries) {
        const comedian = await db.comedian.findFirst({
            where: { youtubeChannelId: entry.channelId as string },
            select: { uuid: true },
        });

        if (!comedian) {
            continue;
        }

        processed += 1;
    }

    return NextResponse.json({ ok: true, processed }, { status: 202 });
});
