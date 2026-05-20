import { NextRequest, NextResponse } from "next/server";
import { getSearchedPodcasts } from "@/lib/data/podcast/search/getSearchedPodcasts";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "podcasts-search");
    if (rl instanceof NextResponse) return rl;

    const sp = req.nextUrl.searchParams;

    try {
        const rawAuthCtx = await resolveAuth(req);
        const authCtx = rawAuthCtx === PROFILE_MISSING ? null : rawAuthCtx;
        const result = await getSearchedPodcasts({
            q: sp.get("q") ?? undefined,
            page: sp.get("page") ?? undefined,
            size: sp.get("size") ?? undefined,
            sort: sp.get("sort") ?? undefined,
            includeEmpty: sp.get("includeEmpty") ?? undefined,
            profileId: authCtx?.profileId,
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
