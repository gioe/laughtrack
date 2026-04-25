import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import {
    checkRateLimit,
    RATE_LIMITS,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";

export async function GET(req: NextRequest) {
    const authCtx = await resolveAuth(req);
    if (authCtx === PROFILE_MISSING) {
        return NextResponse.json({ error: "profile_missing" }, { status: 422 });
    }
    if (!authCtx) {
        return NextResponse.json({ error: "unauthorized" }, { status: 401 });
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
