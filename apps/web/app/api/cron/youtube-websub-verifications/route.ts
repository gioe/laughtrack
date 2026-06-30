import { timingSafeEqual } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { withRequestMetrics } from "@/lib/metrics";
import { verifyPendingYouTubeWebSubEvents } from "@/lib/youtube/youtubeWebSubVerification";

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    if (!hasValidCronBearer(req)) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const apiKey =
        process.env.YOUTUBE_DATA_API_KEY ?? process.env.YOUTUBE_API_KEY;
    if (!apiKey) {
        return NextResponse.json(
            { error: "youtube_api_key_missing" },
            { status: 500 },
        );
    }

    try {
        const result = await verifyPendingYouTubeWebSubEvents({
            dbClient: db,
            apiKey,
        });

        console.info(
            `[cron/youtube-websub-verifications] verified ${result.total} YouTube WebSub events`,
        );

        return NextResponse.json(result);
    } catch (error) {
        console.error("[cron/youtube-websub-verifications] failed:", error);
        return NextResponse.json(
            { error: "youtube_websub_verification_failed" },
            { status: 500 },
        );
    }
});

function hasValidCronBearer(req: NextRequest): boolean {
    const authHeader = req.headers.get("authorization");
    const bearerToken = authHeader?.startsWith("Bearer ")
        ? authHeader.slice(7)
        : null;
    const cronSecret = process.env.CRON_SECRET;

    if (!bearerToken || !cronSecret) {
        return false;
    }

    const bearerBuf = Buffer.from(bearerToken);
    const secretBuf = Buffer.from(cronSecret);

    return (
        bearerBuf.length === secretBuf.length &&
        timingSafeEqual(bearerBuf, secretBuf)
    );
}
