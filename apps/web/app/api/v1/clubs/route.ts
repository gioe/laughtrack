import { NextRequest, NextResponse } from "next/server";
import { getPopularClubs } from "@/lib/data/home/getPopularClubs";
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
        ? `clubs:auth:${session!.profile!.userid}`
        : `clubs:anon:${getClientIp(req)}`;
    const rl = checkRateLimit(
        rateLimitKey,
        isAuthenticated ? RATE_LIMITS.publicReadAuth : RATE_LIMITS.publicRead,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    try {
        const clubs = await getPopularClubs();
        return NextResponse.json(
            { data: clubs },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/clubs error:", error);
        return NextResponse.json(
            { error: "Failed to fetch clubs" },
            { status: 500 },
        );
    }
}
