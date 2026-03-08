import { auth } from "@/auth";
import { generateToken } from "@/util/token";
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
 * Exchanges a valid NextAuth session cookie for a JWT Bearer token (24h).
 * iOS clients use this after completing OAuth via ASWebAuthenticationSession.
 * Browser cross-origin requests are rejected via Origin check to prevent CSRF.
 */
export async function POST(req: NextRequest) {
    const rl = checkRateLimit(
        `auth-token:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    // CSRF: if Origin header is present, it must match an allowed origin.
    // Native iOS URLSession requests do not send Origin, so they pass through.
    const origin = req.headers.get("origin");
    if (origin && !ALLOWED_ORIGINS.includes(origin)) {
        return new NextResponse(null, { status: 403 });
    }

    const session = await auth();
    if (!session?.user?.email) {
        return new NextResponse(null, { status: 401 });
    }

    const token = generateToken({ email: session.user.email }, "access");

    return NextResponse.json({ token }, { headers: rateLimitHeaders(rl) });
}
