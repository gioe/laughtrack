import { NextRequest, NextResponse } from "next/server";
import { findUpcomingRunsForComedian } from "@/lib/data/comedian/detail/findUpcomingRunsForComedian";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { readTimezoneHeader } from "@/util/timezone";

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> },
) {
    const rl = await applyPublicReadRateLimit(
        req,
        "comedians-id-upcoming-runs",
    );
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
    const club = normalizeParam(sp.get("club"));
    const location = normalizeParam(sp.get("location"));
    const date = normalizeParam(sp.get("date"));

    if (date && (!ISO_DATE_RE.test(date) || isNaN(new Date(date).getTime()))) {
        return NextResponse.json(
            { error: "date must be a valid date in YYYY-MM-DD format" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const tzResult = readTimezoneHeader(req);
    if (!tzResult.ok) {
        return NextResponse.json(
            { error: tzResult.error },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    try {
        const rawAuthCtx = await resolveAuth(req);
        const authCtx = rawAuthCtx === PROFILE_MISSING ? null : rawAuthCtx;
        const runs = await findUpcomingRunsForComedian(numericId, {
            club,
            location,
            date,
            timezone: tzResult.timezone,
            ...(authCtx
                ? { profileId: authCtx.profileId, userId: authCtx.userId }
                : {}),
        });

        return NextResponse.json(
            { data: runs },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/comedians/[id]/upcoming-runs error:", error);
        return NextResponse.json(
            { error: "Failed to fetch upcoming runs" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}

function normalizeParam(value: string | null): string | undefined {
    const trimmed = value?.trim();
    return trimmed ? trimmed : undefined;
}
