import { NextRequest, NextResponse } from "next/server";
import { getPodcastEpisodeDetailPageData } from "@/lib/data/podcast/detail/getPodcastEpisodeDetailPageData";
import { publicReadCacheHeaders } from "@/lib/httpCache";
import { withRequestMetrics } from "@/lib/metrics";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { NotFoundError } from "@/objects/NotFoundError";

const POSITIVE_INTEGER_RE = /^[1-9]\d*$/;

function parsePodcastEpisodeId(raw: string): number | null {
    if (!POSITIVE_INTEGER_RE.test(raw)) return null;

    const numericId = Number(raw);
    if (!Number.isSafeInteger(numericId)) return null;

    return numericId;
}

export const GET = withRequestMetrics(async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> },
) {
    const rl = await applyPublicReadRateLimit(req, "podcast-episodes-id");
    if (rl instanceof NextResponse) return rl;

    const { id } = await params;
    const numericId = parsePodcastEpisodeId(id);

    if (numericId === null) {
        return NextResponse.json(
            { error: "Invalid id" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    try {
        const result = await getPodcastEpisodeDetailPageData(numericId);
        return NextResponse.json(result, {
            headers: {
                ...rateLimitHeaders(rl),
                ...publicReadCacheHeaders(),
            },
        });
    } catch (error) {
        if (error instanceof NotFoundError) {
            return NextResponse.json(
                { error: "Podcast episode not found" },
                { status: 404, headers: rateLimitHeaders(rl) },
            );
        }

        console.error("GET /api/v1/podcast-episodes/[id] error:", error);
        return NextResponse.json(
            { error: "Failed to fetch podcast episode" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
});
