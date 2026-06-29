import { timingSafeEqual } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { withRequestMetrics } from "@/lib/metrics";
import {
    renewYouTubeWebSubSubscriptions,
    resolveYouTubeWebSubCallbackUrl,
} from "@/lib/youtube/youtubeWebSubSubscriptions";

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    if (!hasValidCronBearer(req)) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    try {
        const result = await renewYouTubeWebSubSubscriptions({
            dbClient: db,
            callbackUrl: resolveYouTubeWebSubCallbackUrl(process.env),
            logger: console,
        });

        console.info(
            `[cron/youtube-websub-renewals] renewed ${result.succeeded}/${result.total} YouTube WebSub subscriptions`,
        );

        return NextResponse.json({
            total: result.total,
            succeeded: result.succeeded,
            failed: result.failed,
        });
    } catch (error) {
        console.error("[cron/youtube-websub-renewals] failed:", error);
        return NextResponse.json(
            { error: "youtube_websub_renewal_failed" },
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
