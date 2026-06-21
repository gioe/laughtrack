import { NextRequest, NextResponse } from "next/server";
import { withRequestMetrics } from "@/lib/metrics";
import { db } from "@/lib/db";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitResponse,
} from "@/lib/rateLimit";

/**
 * Stamp the notification-center high-water mark. Called when the user opens the
 * notification center; sets notificationsLastSeenAt to now so every existing
 * notification is treated as read and the unread badge clears. New
 * notifications (sentAt > this timestamp) become unread again.
 */
export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    const ipRl = await checkRateLimit(
        `me-notifications-seen-ip:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!ipRl.allowed) return rateLimitResponse(ipRl);

    const authCtx = await resolveAuth(req);
    if (authCtx === PROFILE_MISSING) {
        return NextResponse.json({ error: "profile_missing" }, { status: 422 });
    }
    if (!authCtx) {
        return NextResponse.json({ error: "unauthorized" }, { status: 401 });
    }

    const rl = await checkRateLimit(
        `me-notifications-seen:${authCtx.userId}`,
        RATE_LIMITS.authenticated,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    const updatedProfile = await db.userProfile.update({
        where: { userid: authCtx.userId },
        data: { notificationsLastSeenAt: new Date() },
        select: { notificationsLastSeenAt: true },
    });

    return NextResponse.json({
        data: {
            lastSeenAt:
                updatedProfile.notificationsLastSeenAt?.toISOString() ?? null,
        },
    });
});
