import { NextRequest, NextResponse } from "next/server";
import { getTrendingComedians } from "@/lib/data/home/getTrendingComedians";
import {
    applyPublicReadRateLimit,
    parseLimitParam,
    rateLimitHeaders,
} from "@/lib/rateLimit";

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "comedians");
    if (rl instanceof NextResponse) return rl;

    try {
        const limitOrErr = parseLimitParam(req);
        if (limitOrErr instanceof NextResponse) return limitOrErr;
        const limit = limitOrErr;

        const rawOffset = req.nextUrl.searchParams.get("offset");
        const offset = rawOffset !== null ? Number(rawOffset) : 0;
        if (!Number.isInteger(offset) || offset < 0) {
            return NextResponse.json(
                { error: "offset must be a non-negative integer" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }
        const comedians = await getTrendingComedians(limit, offset);
        return NextResponse.json(
            { data: comedians },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/comedians error:", error);
        return NextResponse.json(
            { error: "Failed to fetch comedians" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
