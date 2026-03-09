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
        const rawLimit = req.nextUrl.searchParams.get("limit");
        const limit = rawLimit !== null ? Number(rawLimit) : 8;
        if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
            return NextResponse.json(
                { error: "limit must be a positive integer between 1 and 100" },
                { status: 400 },
            );
        }
        const clubs = await getPopularClubs(limit);
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
