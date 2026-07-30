import { NextRequest, NextResponse } from "next/server";
import { findClubHighlights } from "@/lib/data/club/detail/findClubHighlights";
import { withRequestMetrics } from "@/lib/metrics";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

const HIGHLIGHTS_CACHE_CONTROL =
    "public, max-age=60, s-maxage=300, stale-while-revalidate=300";

export const GET = withRequestMetrics(async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> },
) {
    const rl = await applyPublicReadRateLimit(req, "clubs-id-highlights");
    if (rl instanceof NextResponse) return rl;

    const { id } = await params;
    const numericId = Number(id);
    if (!Number.isInteger(numericId)) {
        return NextResponse.json(
            { error: "Invalid id" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    try {
        const highlights = await findClubHighlights(numericId);
        if (!highlights) {
            return NextResponse.json(
                { error: "Club not found" },
                { status: 404, headers: rateLimitHeaders(rl) },
            );
        }

        return NextResponse.json(
            { data: highlights },
            {
                headers: {
                    ...rateLimitHeaders(rl),
                    "Cache-Control": HIGHLIGHTS_CACHE_CONTROL,
                },
            },
        );
    } catch (error) {
        console.error("GET /api/v1/clubs/[id]/highlights error:", error);
        return NextResponse.json(
            { error: "Failed to fetch club highlights" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
});
