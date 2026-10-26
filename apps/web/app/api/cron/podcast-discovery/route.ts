import { timingSafeEqual } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { refreshPodcastDiscoverySnapshot } from "@/lib/data/home/podcastDiscoverySnapshot";
import { withRequestMetrics } from "@/lib/metrics";

export const maxDuration = 60;

async function refresh(request: NextRequest) {
    const expected = process.env.CRON_SECRET;
    const actual = request.headers.get("authorization");
    if (
        !expected ||
        !actual ||
        Buffer.byteLength(actual) !== Buffer.byteLength(`Bearer ${expected}`) ||
        !timingSafeEqual(Buffer.from(actual), Buffer.from(`Bearer ${expected}`))
    ) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    try {
        return NextResponse.json(await refreshPodcastDiscoverySnapshot());
    } catch (error) {
        console.error("[cron/podcast-discovery] refresh failed", error);
        return NextResponse.json(
            { error: "Snapshot refresh failed" },
            { status: 500 },
        );
    }
}

export const GET = withRequestMetrics(refresh);
export const POST = withRequestMetrics(refresh);
