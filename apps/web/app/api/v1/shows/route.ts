import { NextRequest, NextResponse } from "next/server";
import { getSearchedShows } from "@/lib/data/show/search/getSearchedShows";
import { resolveAuth } from "@/lib/auth/resolveAuth";

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const DEFAULT_DISTANCE = "25";

export async function GET(req: NextRequest) {
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
            { status: 400 },
        );
    }

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

    const params = new URLSearchParams();
    params.set("zip", zip);
    // Distance defaults to 25 miles so zip geo-filtering is always applied
    params.set("distance", distance ?? DEFAULT_DISTANCE);
    if (from) params.set("fromDate", from);
    if (to) params.set("toDate", to);
    // QueryHelper uses 1-indexed pages internally; API is 0-indexed
    if (page !== null)
        params.set("page", String(Math.max(0, Number(page)) + 1));
    if (size !== null) params.set("size", size);
    if (comedian) params.set("comedian", comedian);
    if (filters) params.set("filters", filters);

    const timezone = req.headers.get("X-Timezone") ?? "UTC";

    try {
        const authCtx = await resolveAuth(req);
        const result = await getSearchedShows({
            params: params.toString(),
            timezone,
            ...(authCtx
                ? { profileId: authCtx.profileId, userId: authCtx.userId }
                : {}),
        });

        return NextResponse.json({
            total: result.total,
            data: result.data,
            filters: result.filters,
        });
    } catch (error) {
        console.error("GET /api/v1/shows error:", error);
        return NextResponse.json(
            { error: "Failed to fetch shows" },
            { status: 500 },
        );
    }
}
