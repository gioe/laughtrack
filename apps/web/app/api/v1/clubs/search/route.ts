import { NextRequest, NextResponse } from "next/server";
import { getSearchedClubs } from "@/lib/data/club/search/getSearchedClubs";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { readTimezoneHeader } from "@/util/timezone";
import { auth } from "@/auth";

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "clubs-search");
    if (rl instanceof NextResponse) return rl;

    const sp = req.nextUrl.searchParams;
    const club = sp.get("club") ?? undefined;
    const sort = sp.get("sort") ?? undefined;
    const filters = sp.get("filters") ?? undefined;
    const chain = sp.get("chain") ?? undefined;
    const page = sp.get("page");
    const size = sp.get("size") ?? undefined;
    const includeEmpty = sp.get("includeEmpty") ?? undefined;

    const tzResult = readTimezoneHeader(req);
    if (!tzResult.ok) {
        return NextResponse.json(
            { error: tzResult.error },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }
    const timezone = tzResult.timezone;

    try {
        const session = await auth();
        const profileId = session?.profile?.id;
        const userId = session?.profile?.userid;

        const result = await getSearchedClubs({
            params: {
                club,
                sort,
                filters,
                chain,
                // QueryHelper uses 1-indexed pages; API is 0-indexed
                page:
                    page !== null && page !== undefined
                        ? String(Math.max(0, Number(page)) + 1)
                        : undefined,
                size,
                includeEmpty,
            },
            timezone,
            ...(profileId ? { profileId, userId } : {}),
        });

        return NextResponse.json(
            { data: result.data, total: result.total, filters: result.filters },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/clubs/search error:", error);
        return NextResponse.json(
            { error: "Failed to fetch clubs" },
            { status: 500 },
        );
    }
}
