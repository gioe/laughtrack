import { NextRequest, NextResponse } from "next/server";
import { getTrendingComedians } from "@/lib/data/home/getTrendingComedians";
import { auth } from "@/auth";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";

export async function GET(req: NextRequest) {
    const session = await auth();
    const isAuthenticated = !!session?.profile;
    const rateLimitKey = isAuthenticated
        ? `comedians:auth:${session!.profile!.userid}`
        : `comedians:anon:${getClientIp(req)}`;
    const rl = checkRateLimit(
        rateLimitKey,
        isAuthenticated ? RATE_LIMITS.publicReadAuth : RATE_LIMITS.publicRead,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    try {
        const rawLimit = req.nextUrl.searchParams.get("limit");
        const limit = rawLimit !== null ? Number(rawLimit) : 8;
        if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
            return NextResponse.json(
                { error: "limit must be a positive integer between 1 and 100" },
                { status: 400 },
            );
        }
        const rawOffset = req.nextUrl.searchParams.get("offset");
        const offset = rawOffset !== null ? parseInt(rawOffset, 10) : 0;
        if (!Number.isInteger(offset) || offset < 0) {
            return NextResponse.json(
                { error: "offset must be a non-negative integer" },
                { status: 400 },
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
            { status: 500 },
        );
    }
}
