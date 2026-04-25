import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";

export async function GET(req: NextRequest) {
    // Pre-auth IP rate limit protects resolveAuth() / auth() from
    // unauthenticated probes — matches the /auth/signout pattern.
    const ipRl = await checkRateLimit(
        `me-ip:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!ipRl.allowed) return rateLimitResponse(ipRl);

    const authCtx = await resolveAuth(req);
    if (authCtx === PROFILE_MISSING) {
        return NextResponse.json(
            { error: "profile_missing" },
            { status: 422, headers: rateLimitHeaders(ipRl) },
        );
    }
    if (!authCtx) {
        return NextResponse.json(
            { error: "unauthorized" },
            { status: 401, headers: rateLimitHeaders(ipRl) },
        );
    }

    const rl = await checkRateLimit(
        `me:${authCtx.userId}`,
        RATE_LIMITS.authenticated,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    const user = await db.user.findUnique({
        where: { id: authCtx.userId },
        select: { name: true, email: true, image: true },
    });
    if (!user) {
        return NextResponse.json(
            { error: "unauthorized" },
            { status: 401, headers: rateLimitHeaders(rl) },
        );
    }

    return NextResponse.json(
        {
            data: {
                display_name: user.name,
                email: user.email,
                avatar_url: user.image,
            },
        },
        { headers: rateLimitHeaders(rl) },
    );
}
