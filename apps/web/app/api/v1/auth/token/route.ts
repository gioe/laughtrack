import { auth } from "@/auth";
import { db } from "@/lib/db";
import { issueRefreshToken } from "@/lib/auth/refreshTokens";
import { ACCESS_TOKEN_TTL_SECONDS, generateAccessToken } from "@/util/token";
import { NextRequest, NextResponse } from "next/server";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";

const ALLOWED_ORIGINS = (
    process.env.CORS_ALLOWED_ORIGINS ??
    process.env.NEXT_PUBLIC_WEBSITE_URL ??
    ""
)
    .split(",")
    .map((o) => o.trim())
    .filter(Boolean);

/**
 * POST /api/v1/auth/token
 * Exchanges a valid NextAuth session cookie for a short-lived access JWT
 * plus a long-lived opaque refresh token. iOS clients call this after
 * completing OAuth via ASWebAuthenticationSession.
 * Browser cross-origin requests are rejected via Origin check to prevent CSRF.
 */
export async function POST(req: NextRequest) {
    const rl = await checkRateLimit(
        `auth-token:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    const origin = req.headers.get("origin");
    if (origin && !ALLOWED_ORIGINS.includes(origin)) {
        return new NextResponse(null, { status: 403 });
    }

    const session = await auth();
    if (!session?.user?.email) {
        return new NextResponse(null, { status: 401 });
    }

    const user = await db.user.findUnique({
        where: { email: session.user.email },
        select: { id: true },
    });
    if (!user) {
        return new NextResponse(null, { status: 401 });
    }

    const accessToken = generateAccessToken({ email: session.user.email });
    const { token: refreshToken } = await issueRefreshToken(user.id);

    return NextResponse.json(
        {
            accessToken,
            refreshToken,
            expiresIn: ACCESS_TOKEN_TTL_SECONDS,
        },
        { headers: rateLimitHeaders(rl) },
    );
}
