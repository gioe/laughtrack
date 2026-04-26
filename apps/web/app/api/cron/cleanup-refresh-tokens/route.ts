import { cleanupExpiredRefreshTokens } from "@/lib/auth/refreshTokens";
import { timingSafeEqual } from "crypto";
import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/cron/cleanup-refresh-tokens
 * Deletes expired or long-revoked refresh tokens. Intended to be invoked by a
 * scheduled job (GitHub Actions) using a Bearer token matching CRON_SECRET.
 *
 * Without periodic cleanup the refresh_tokens table grows unboundedly: each
 * active user rotates 2+ tokens per day on a 30-day TTL, and the unique index
 * on `token` plus the per-user updateMany on sign-out both slow down with size.
 */
export async function POST(req: NextRequest) {
    const authHeader = req.headers.get("authorization");
    const bearerToken = authHeader?.startsWith("Bearer ")
        ? authHeader.slice(7)
        : null;

    const cronSecret = process.env.CRON_SECRET;
    const hasValidBearer =
        bearerToken &&
        cronSecret &&
        bearerToken.length === cronSecret.length &&
        timingSafeEqual(Buffer.from(bearerToken), Buffer.from(cronSecret));

    if (!hasValidBearer) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { deleted } = await cleanupExpiredRefreshTokens();
    return NextResponse.json({ deleted });
}
