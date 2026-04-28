import { NextRequest, NextResponse } from "next/server";
import { getSearchedComedians } from "@/lib/data/comedian/search/getSearchedComedians";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { readTimezoneHeader } from "@/util/timezone";
import { auth } from "@/auth";
import { UserRole } from "@/objects/enum/userRole";

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "comedians-search");
    if (rl instanceof NextResponse) return rl;

    const sp = req.nextUrl.searchParams;
    const comedian = sp.get("comedian") ?? undefined;
    const sort = sp.get("sort") ?? undefined;
    const filters = sp.get("filters") ?? undefined;
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
        const isAdmin = session?.profile?.role === UserRole.Admin;

        const result = await getSearchedComedians({
            params: {
                comedian,
                sort,
                filters,
                includeEmpty,
                // QueryHelper uses 1-indexed pages; API is 0-indexed
                page:
                    page !== null && page !== undefined
                        ? String(Math.max(0, Number(page)) + 1)
                        : undefined,
                size,
            },
            timezone,
            ...(profileId ? { profileId, userId } : {}),
            isAdmin,
        });

        return NextResponse.json(
            { data: result.data, total: result.total, filters: result.filters },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/comedians/search error:", error);
        return NextResponse.json(
            { error: "Failed to fetch comedians" },
            { status: 500 },
        );
    }
}
