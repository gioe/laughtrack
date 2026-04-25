import {
    consumeRefreshToken,
    issueRefreshToken,
} from "@/lib/auth/refreshTokens";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";
import { ACCESS_TOKEN_TTL_SECONDS, generateAccessToken } from "@/util/token";
import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/v1/auth/refresh
 * Exchanges a valid refresh token for a new access token plus a rotated
 * refresh token. The submitted refresh token is revoked atomically — a
 * subsequent call with the same token returns 401.
 */
export async function POST(req: NextRequest) {
    const rl = await checkRateLimit(
        `auth-refresh:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    let body: unknown;
    try {
        body = await req.json();
    } catch {
        return NextResponse.json(
            { error: "invalid_body" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const refreshToken =
        body && typeof body === "object" && "refreshToken" in body
            ? (body as { refreshToken: unknown }).refreshToken
            : undefined;
    if (typeof refreshToken !== "string" || refreshToken.length === 0) {
        return NextResponse.json(
            { error: "missing_refresh_token" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const resolved = await consumeRefreshToken(refreshToken);
    if (typeof resolved === "string") {
        console.info(
            `[auth/refresh] rejected refresh token: reason=${resolved}`,
        );
        return NextResponse.json(
            { error: "invalid_refresh_token" },
            { status: 401, headers: rateLimitHeaders(rl) },
        );
    }
    if ("status" in resolved) {
        console.warn(
            `[auth/refresh] refresh token reuse detected userId=${resolved.userId}; revoked ${resolved.familyRevokedCount} sibling token(s)`,
        );
        return NextResponse.json(
            { error: "invalid_refresh_token" },
            { status: 401, headers: rateLimitHeaders(rl) },
        );
    }

    const accessToken = generateAccessToken({ email: resolved.userEmail });
    const { token: newRefreshToken } = await issueRefreshToken(resolved.userId);

    return NextResponse.json(
        {
            accessToken,
            refreshToken: newRefreshToken,
            expiresIn: ACCESS_TOKEN_TTL_SECONDS,
        },
        { headers: rateLimitHeaders(rl) },
    );
}
