import { PROFILE_MISSING, resolveAuth } from "@/lib/auth/resolveAuth";
import {
    revokeAllRefreshTokens,
    revokeRefreshToken,
} from "@/lib/auth/refreshTokens";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";
import { withRequestMetrics } from "@/lib/metrics";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const signoutRequestSchema = z.object({
    refreshToken: z.string().min(1),
    platform: z.enum(["ios", "android"]),
    appVersion: z
        .string()
        .min(1)
        .max(64)
        .regex(/^[A-Za-z0-9._+()-]+$/),
    source: z.enum(["profile"]),
});

/**
 * POST /api/v1/auth/signout
 * Revokes the caller-owned refresh token supplied by current native clients.
 * Empty-body requests from already-shipped clients retain the legacy behavior
 * of revoking every active refresh token belonging to the caller.
 */
export const POST = withRequestMetrics(async function POST(req: NextRequest) {
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

    let rawBody: string;
    try {
        rawBody = await req.text();
    } catch {
        return NextResponse.json(
            { error: "invalid_body" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    if (rawBody.trim().length === 0) {
        const revoked = await revokeAllRefreshTokens(authCtx.userId);
        console.info(
            `[auth/signout] userId=${authCtx.userId} mode=legacy revoked=${revoked} platform=unknown appVersion=unknown source=unknown`,
        );
        return NextResponse.json(
            { revoked },
            { headers: rateLimitHeaders(rl) },
        );
    }

    let body: unknown;
    try {
        body = JSON.parse(rawBody);
    } catch {
        return NextResponse.json(
            { error: "invalid_body" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const parsed = signoutRequestSchema.safeParse(body);
    if (!parsed.success) {
        return NextResponse.json(
            { error: "invalid_body" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const { refreshToken, platform, appVersion, source } = parsed.data;
    const revoked = await revokeRefreshToken(authCtx.userId, refreshToken);
    console.info(
        `[auth/signout] userId=${authCtx.userId} mode=scoped revoked=${revoked} platform=${platform} appVersion=${appVersion} source=${source}`,
    );

    return NextResponse.json({ revoked }, { headers: rateLimitHeaders(rl) });
});
