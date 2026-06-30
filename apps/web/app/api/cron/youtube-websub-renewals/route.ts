import { timingSafeEqual } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { withRequestMetrics } from "@/lib/metrics";
import {
    syncYouTubeWebSubSubscriptions,
    resolveYouTubeWebSubCallbackUrl,
} from "@/lib/youtube/youtubeWebSubSubscriptions";

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    if (!hasValidCronBearer(req)) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // ?dryRun=1 reports the intended subscribe/renew/unsubscribe plan without any
    // hub or DB writes — useful for verifying gating before enabling ingestion.
    const dryRun = isTruthyParam(req.nextUrl.searchParams.get("dryRun"));

    try {
        const result = await syncYouTubeWebSubSubscriptions({
            dbClient: db,
            callbackUrl: resolveYouTubeWebSubCallbackUrl(process.env),
            logger: console,
            dryRun,
        });

        if (result.gated) {
            console.info(
                "[cron/youtube-websub-renewals] skipped — global feed ingestion disabled",
            );
        } else {
            console.info(
                `[cron/youtube-websub-renewals] ${dryRun ? "planned" : "synced"} ` +
                    `${result.succeeded}/${result.total} actions ` +
                    `(subscribe=${result.counts.subscribe} renew=${result.counts.renew} ` +
                    `unsubscribe=${result.counts.unsubscribe} skip=${result.counts.skip})`,
            );
        }

        return NextResponse.json({
            gated: result.gated,
            dryRun: result.dryRun,
            total: result.total,
            succeeded: result.succeeded,
            failed: result.failed,
            counts: result.counts,
        });
    } catch (error) {
        console.error("[cron/youtube-websub-renewals] failed:", error);
        return NextResponse.json(
            { error: "youtube_websub_renewal_failed" },
            { status: 500 },
        );
    }
});

function isTruthyParam(value: string | null): boolean {
    return value === "1" || value === "true";
}

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
