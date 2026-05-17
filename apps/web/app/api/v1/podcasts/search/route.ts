import { NextRequest, NextResponse } from "next/server";
import { getSearchedPodcasts } from "@/lib/data/podcast/search/getSearchedPodcasts";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "podcasts-search");
    if (rl instanceof NextResponse) return rl;

    const sp = req.nextUrl.searchParams;

    try {
        const result = await getSearchedPodcasts({
            q: sp.get("q") ?? undefined,
            page: sp.get("page") ?? undefined,
            size: sp.get("size") ?? undefined,
        });

        return NextResponse.json(result, { headers: rateLimitHeaders(rl) });
    } catch (error) {
        console.error("GET /api/v1/podcasts/search error:", error);
        return NextResponse.json(
            { error: "Failed to fetch podcasts" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
