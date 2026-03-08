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
        const comedians = await getTrendingComedians();
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
