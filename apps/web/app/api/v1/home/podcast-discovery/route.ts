import { createHash } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { readPodcastDiscoverySnapshot } from "@/lib/data/home/podcastDiscoverySnapshot";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { withRequestMetrics } from "@/lib/metrics";

export const GET = withRequestMetrics(async function GET(request: NextRequest) {
    const limit = await applyPublicReadRateLimit(
        request,
        "home-podcast-discovery",
    );
    if (limit instanceof NextResponse) return limit;
    try {
        const data = await readPodcastDiscoverySnapshot();
        const body = JSON.stringify({ data });
        const etag = `"${createHash("sha256").update(body).digest("hex")}"`;
        const headers = {
            ...rateLimitHeaders(limit),
            // Shared public selection, but revalidate on each visit so a cached
            // response cannot conceal a moderation invalidation. No stale-on-error.
            "Cache-Control": "public, no-cache, must-revalidate",
            ETag: etag,
        };
        if (request.headers.get("if-none-match") === etag) {
            return new NextResponse(null, { status: 304, headers });
        }
        return new NextResponse(body, {
            headers: { ...headers, "Content-Type": "application/json" },
        });
    } catch (error) {
        console.error("[home/podcast-discovery] snapshot read failed", error);
        return NextResponse.json(
            { error: "Podcast discovery unavailable" },
            {
                status: 503,
                headers: {
                    ...rateLimitHeaders(limit),
                    "Cache-Control": "no-store",
                },
            },
        );
    }
});
