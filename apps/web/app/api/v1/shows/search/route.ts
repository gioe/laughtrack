import { NextRequest, NextResponse } from "next/server";
import { getSearchedShows } from "@/lib/data/show/search/getSearchedShows";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { readTimezoneHeader } from "@/util/timezoneHeader";

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const DEFAULT_DISTANCE = "25";

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "shows-search");
    if (rl instanceof NextResponse) return rl;

    const sp = req.nextUrl.searchParams;
    const zip = sp.get("zip") ?? undefined;
    const from = sp.get("from");
    const to = sp.get("to");
    const page = sp.get("page");
    const size = sp.get("size") ?? undefined;
    const comedian = sp.get("comedian") ?? undefined;
    const club = sp.get("club") ?? undefined;
    const filters = sp.get("filters") ?? undefined;
    const distance = sp.get("distance");
    const sort = sp.get("sort") ?? undefined;

    if (from && (!ISO_DATE_RE.test(from) || isNaN(new Date(from).getTime()))) {
        return NextResponse.json(
            { error: "from must be a valid date in YYYY-MM-DD format" },
            { status: 400 },
        );
    }

    if (to && (!ISO_DATE_RE.test(to) || isNaN(new Date(to).getTime()))) {
        return NextResponse.json(
            { error: "to must be a valid date in YYYY-MM-DD format" },
            { status: 400 },
        );
    }

    if (distance !== null && distance !== undefined) {
        const distanceNum = Number(distance);
        if (isNaN(distanceNum) || distanceNum < 1 || distanceNum > 500) {
            return NextResponse.json(
                { error: "distance must be a number between 1 and 500 miles" },
                { status: 400 },
            );
        }
    }

    const tzResult = readTimezoneHeader(req);
    if (!tzResult.ok) {
        return NextResponse.json(
            { error: tzResult.error },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }
    const timezone = tzResult.timezone;

    try {
        const rawAuthCtx = await resolveAuth(req);
        const authCtx = rawAuthCtx === PROFILE_MISSING ? null : rawAuthCtx;

        const result = await getSearchedShows({
            params: {
                zip,
                distance: distance ?? (zip ? DEFAULT_DISTANCE : undefined),
                fromDate: from ?? undefined,
                toDate: to ?? undefined,
                // QueryHelper uses 1-indexed pages; API is 0-indexed
                page:
                    page !== null && page !== undefined
                        ? String(Math.max(0, Number(page)) + 1)
                        : undefined,
                size,
                comedian,
                club,
                filters,
                sort,
            },
            timezone,
            ...(authCtx
                ? { profileId: authCtx.profileId, userId: authCtx.userId }
                : {}),
        });

        return NextResponse.json(
            {
                data: result.data,
                total: result.total,
                filters: result.filters,
                zipCapTriggered: result.zipCapTriggered,
            },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/shows/search error:", error);
        return NextResponse.json(
            { error: "Failed to fetch shows" },
            { status: 500 },
        );
    }
}
