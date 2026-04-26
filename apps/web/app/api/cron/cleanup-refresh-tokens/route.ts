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
    let hasValidBearer = false;
    if (bearerToken && cronSecret) {
        // Compare byte lengths, not JS string lengths — multi-byte UTF-8 chars
        // can encode to different byte counts at equal code-unit lengths, which
        // would crash timingSafeEqual with a RangeError.
        const bearerBuf = Buffer.from(bearerToken);
        const secretBuf = Buffer.from(cronSecret);
        if (bearerBuf.length === secretBuf.length) {
            hasValidBearer = timingSafeEqual(bearerBuf, secretBuf);
        }
    }

    if (!hasValidBearer) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    try {
        const { deleted } = await cleanupExpiredRefreshTokens();
        console.info(
            `[cron/cleanup-refresh-tokens] deleted ${deleted} refresh tokens`,
        );
        return NextResponse.json({ deleted });
    } catch (err) {
        console.error("[cron/cleanup-refresh-tokens] failed:", err);
        return NextResponse.json({ error: "cleanup_failed" }, { status: 500 });
    }
}
