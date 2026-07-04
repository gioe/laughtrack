import { NextRequest, NextResponse } from "next/server";
import { findUpcomingShowsForClub } from "@/lib/data/show/search/findShowsWithCount";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { withRequestMetrics } from "@/lib/metrics";
import { personalizedReadCacheHeaders } from "@/lib/httpCache";

export const GET = withRequestMetrics(async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> },
) {
    const rl = await applyPublicReadRateLimit(req, "clubs-id-shows");
    if (rl instanceof NextResponse) return rl;

    const { id } = await params;
    const numericId = Number(id);

    if (!Number.isInteger(numericId)) {
        return NextResponse.json(
            { error: "Invalid id" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const sp = req.nextUrl.searchParams;
    const page = sp.get("page");
    const size = sp.get("size");

    if (
        page !== null &&
        (!Number.isInteger(Number(page)) || Number(page) < 0)
    ) {
        return NextResponse.json(
            { error: "page must be a non-negative integer" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    if (
        size !== null &&
        (!Number.isInteger(Number(size)) || Number(size) < 1)
    ) {
        return NextResponse.json(
            { error: "size must be a positive integer" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    try {
        const rawAuthCtx = await resolveAuth(req);
        const authCtx = rawAuthCtx === PROFILE_MISSING ? null : rawAuthCtx;
        const result = await findUpcomingShowsForClub(numericId, {
            // QueryHelper uses 1-indexed pages internally; API is 0-indexed.
            page: page !== null ? String(Number(page) + 1) : undefined,
            size: size ?? undefined,
            ...(authCtx
                ? { profileId: authCtx.profileId, userId: authCtx.userId }
                : {}),
        });

        return NextResponse.json(
            {
                data: result.shows,
                total: result.totalCount,
            },
            { headers: { ...rateLimitHeaders(rl), ...personalizedReadCacheHeaders(req, { authed: authCtx !== null }) } },
        );
    } catch (error) {
        console.error("GET /api/v1/clubs/[id]/shows error:", error);
        return NextResponse.json(
            { error: "Failed to fetch club shows" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
});
