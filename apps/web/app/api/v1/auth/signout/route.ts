import { PROFILE_MISSING, resolveAuth } from "@/lib/auth/resolveAuth";
import { revokeAllRefreshTokens } from "@/lib/auth/refreshTokens";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";
import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/v1/auth/signout
 * Revokes every active refresh token belonging to the caller. Requires a
 * valid Bearer access token. iOS clients should still wipe their local
 * keychain entries after receiving a 200 response.
 */
export async function POST(req: NextRequest) {
    const rl = await checkRateLimit(
        `auth-signout:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    const authCtx = await resolveAuth(req);
    if (authCtx === PROFILE_MISSING) {
        return NextResponse.json(
            { error: "profile_missing" },
            { status: 422, headers: rateLimitHeaders(rl) },
        );
    }
    if (!authCtx) {
        return NextResponse.json(
            { error: "unauthorized" },
            { status: 401, headers: rateLimitHeaders(rl) },
        );
    }

    const revoked = await revokeAllRefreshTokens(authCtx.userId);

    return NextResponse.json({ revoked }, { headers: rateLimitHeaders(rl) });
}
