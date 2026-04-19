import { NextRequest, NextResponse } from "next/server";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import {
    findPastShowsForComedian,
    PAST_SHOWS_PAGE_SIZE,
} from "@/lib/data/comedian/detail/findPastShowsForComedian";

const MAX_PAGE_SIZE = 50;

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "comedians-past-shows");
    if (rl instanceof NextResponse) return rl;

    const sp = req.nextUrl.searchParams;
    const comedian = sp.get("comedian") ?? undefined;
    const pageParam = sp.get("page");
    const sizeParam = sp.get("size");

    if (!comedian) {
        return NextResponse.json(
            { error: "comedian is required" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    let page = 0;
    if (pageParam !== null) {
        const parsed = Number(pageParam);
        if (!Number.isInteger(parsed) || parsed < 0) {
            return NextResponse.json(
                { error: "page must be a non-negative integer" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }
        page = parsed;
    }

    let size = PAST_SHOWS_PAGE_SIZE;
    if (sizeParam !== null) {
        const parsed = Number(sizeParam);
        if (!Number.isInteger(parsed) || parsed < 1) {
            return NextResponse.json(
                { error: "size must be a positive integer" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }
        size = Math.min(MAX_PAGE_SIZE, parsed);
    }

    const timezone = req.headers.get("X-Timezone") ?? "UTC";

    try {
        const rawAuthCtx = await resolveAuth(req);
        const authCtx = rawAuthCtx === PROFILE_MISSING ? null : rawAuthCtx;

        const helper = new QueryHelper({
            params: { comedian },
            timezone,
            ...(authCtx
                ? { profileId: authCtx.profileId, userId: authCtx.userId }
                : {}),
        });

        const result = await findPastShowsForComedian(helper, { page, size });

        return NextResponse.json(
            { data: result.shows, total: result.totalCount },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/comedians/past-shows error:", error);
        return NextResponse.json(
            { error: "Failed to fetch past shows" },
            { status: 500 },
        );
    }
}
