import { NextRequest, NextResponse } from "next/server";
import { getSearchedShows } from "@/lib/data/show/search/getSearchedShows";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { SearchParams } from "@/objects/interface";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { readTimezoneHeader } from "@/util/timezoneHeader";

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const DEFAULT_DISTANCE = "25";

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "shows");
    if (rl instanceof NextResponse) return rl;

    const searchParams = req.nextUrl.searchParams;

    const zip = searchParams.get("zip");
    const from = searchParams.get("from");
    const to = searchParams.get("to");
    const page = searchParams.get("page");
    const size = searchParams.get("size");
    const comedian = searchParams.get("comedian");
    const filters = searchParams.get("filters");
    const distance = searchParams.get("distance");

    if (!zip || !/^\d{5}$/.test(zip)) {
        return NextResponse.json(
            { error: "zip is required and must be a 5-digit US zip code" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    if (from && (!ISO_DATE_RE.test(from) || isNaN(new Date(from).getTime()))) {
        return NextResponse.json(
            { error: "from must be a valid date in YYYY-MM-DD format" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    if (to && (!ISO_DATE_RE.test(to) || isNaN(new Date(to).getTime()))) {
        return NextResponse.json(
            { error: "to must be a valid date in YYYY-MM-DD format" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    if (distance !== null) {
        const distanceNum = Number(distance);
        if (isNaN(distanceNum) || distanceNum < 1 || distanceNum > 500) {
            return NextResponse.json(
                { error: "distance must be a number between 1 and 500 miles" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }
    }

    const params: SearchParams = {
        zip,
        // Distance defaults to 25 miles so zip geo-filtering is always applied
        distance: distance ?? DEFAULT_DISTANCE,
        fromDate: from ?? undefined,
        toDate: to ?? undefined,
        // QueryHelper uses 1-indexed pages internally; API is 0-indexed
        page: page !== null ? String(Math.max(0, Number(page)) + 1) : undefined,
        size: size ?? undefined,
        comedian: comedian ?? undefined,
        filters: filters ?? undefined,
    };

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
            params,
            timezone,
            ...(authCtx
                ? { profileId: authCtx.profileId, userId: authCtx.userId }
                : {}),
        });

        return NextResponse.json(
            { total: result.total, data: result.data, filters: result.filters },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/shows error:", error);
        return NextResponse.json(
            { error: "Failed to fetch shows" },
            { status: 500 },
        );
    }
}
