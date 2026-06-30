import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { issueRefreshToken } from "@/lib/auth/refreshTokens";
import { ACCESS_TOKEN_TTL_SECONDS, generateAccessToken } from "@/util/token";
import { withRequestMetrics } from "@/lib/metrics";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";

type TestTokenRequest = {
    email?: unknown;
};

function isEnabled() {
    return (
        process.env.ENABLE_TEST_AUTH === "1" &&
        process.env.VERCEL_ENV !== "production"
    );
}

function allowedEmails() {
    return new Set(
        (process.env.TEST_AUTH_EMAIL_ALLOWLIST ?? "")
            .split(",")
            .map((email) => email.trim().toLowerCase())
            .filter(Boolean),
    );
}

/**
 * POST /api/v1/auth/test-token
 *
 * Staging/local-only shortcut for iOS simulator testing. It intentionally still
 * returns the same native access JWT + opaque refresh token pair as the normal
 * ASWebAuthenticationSession flow, so downstream API auth is unchanged.
 */
export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    const rl = await checkRateLimit(
        `auth-test-token:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    if (!isEnabled()) {
        return new NextResponse(null, { status: 404 });
    }

    const configuredSecret = process.env.TEST_AUTH_SECRET ?? "";
    const providedSecret = req.headers.get("x-test-auth-secret") ?? "";
    if (!configuredSecret || providedSecret !== configuredSecret) {
        return NextResponse.json(
            { error: "unauthorized" },
            { status: 401, headers: rateLimitHeaders(rl) },
        );
    }

    let body: TestTokenRequest;
    try {
        body = (await req.json()) as TestTokenRequest;
    } catch {
        return NextResponse.json(
            { error: "invalid_body" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const email =
        typeof body.email === "string" ? body.email.trim().toLowerCase() : "";
    if (!email || !allowedEmails().has(email)) {
        return NextResponse.json(
            { error: "forbidden" },
            { status: 403, headers: rateLimitHeaders(rl) },
        );
    }

    const user = await db.user.findUnique({
        where: { email },
        select: { id: true, email: true },
    });
    if (!user) {
        return NextResponse.json(
            { error: "user_not_found" },
            { status: 401, headers: rateLimitHeaders(rl) },
        );
    }

    const accessToken = generateAccessToken({ email: user.email });
    const { token: refreshToken } = await issueRefreshToken(user.id);

    return NextResponse.json(
        {
            accessToken,
            refreshToken,
            expiresIn: ACCESS_TOKEN_TTL_SECONDS,
        },
        { headers: rateLimitHeaders(rl) },
    );
});
