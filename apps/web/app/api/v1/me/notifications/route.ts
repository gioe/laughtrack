import { NextRequest, NextResponse } from "next/server";
import { withRequestMetrics } from "@/lib/metrics";
import { z } from "zod";
import { db } from "@/lib/db";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import {
    checkRateLimit,
    getClientIp,
    RATE_LIMITS,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";

/**
 * One notification-center item. Today the only notification type is the
 * comedian-arrival alert, whose copy is template-derived from (comedian, show,
 * club) — so we reconstruct the title/body at read time from the join rather
 * than persisting rendered content. Email and push deliveries for the same
 * (comedianId, showId) collapse into a single item; `channels` records which
 * channels fired.
 */
interface NotificationItem {
    id: string;
    title: string;
    body: string;
    comedianId: string;
    comedianName: string;
    showId: number;
    showPageUrl: string | null;
    showDate: string | null;
    clubName: string | null;
    city: string | null;
    state: string | null;
    channels: string[];
    sentAt: string;
    isUnread: boolean;
}

// Cap the history fetch so a long-tenured user with thousands of sent
// notifications never triggers an unbounded query + join payload on every load
// of the notification center. The cap counts pre-grouping rows; email+push for
// the same event collapse afterward, so the rendered item count can be lower.
const NOTIFICATIONS_FETCH_LIMIT = 100;

const NotificationPreferenceUpdateSchema = z
    .object({
        emailShowNotifications: z.boolean().optional(),
        pushShowNotifications: z.boolean().optional(),
    })
    .refine(
        (data) =>
            data.emailShowNotifications !== undefined ||
            data.pushShowNotifications !== undefined,
        {
            message: "At least one notification preference must be provided",
        },
    );

export const GET = withRequestMetrics(async function GET(req: NextRequest) {
    const ipRl = await checkRateLimit(
        `me-notifications-ip:${getClientIp(req)}`,
        RATE_LIMITS.authToken,
    );
    if (!ipRl.allowed) return rateLimitResponse(ipRl);

    const authCtx = await resolveAuth(req);
    if (authCtx === PROFILE_MISSING) {
        return NextResponse.json(
            { error: "profile_missing" },
            { status: 422, headers: rateLimitHeaders(ipRl) },
        );
    }
    if (!authCtx) {
        return NextResponse.json(
            { error: "unauthorized" },
            { status: 401, headers: rateLimitHeaders(ipRl) },
        );
    }

    const rl = await checkRateLimit(
        `me-notifications:${authCtx.userId}`,
        RATE_LIMITS.authenticated,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    const profile = await db.userProfile.findUnique({
        where: { id: authCtx.profileId },
        select: { notificationsLastSeenAt: true },
    });
    const lastSeenAt = profile?.notificationsLastSeenAt ?? null;

    // Newest first so the first row seen per group carries the latest sentAt.
    const rows = await db.sentNotification.findMany({
        where: { userId: authCtx.userId },
        orderBy: { sentAt: "desc" },
        take: NOTIFICATIONS_FETCH_LIMIT,
        select: {
            comedianId: true,
            showId: true,
            notificationType: true,
            sentAt: true,
            comedian: { select: { name: true } },
            show: {
                select: {
                    date: true,
                    showPageUrl: true,
                    club: { select: { name: true, city: true, state: true } },
                },
            },
        },
    });

    // Collapse email+push rows for the same (comedianId, showId) into one item.
    const groups = new Map<string, NotificationItem>();
    for (const row of rows) {
        const key = `${row.comedianId}:${row.showId}`;
        const existing = groups.get(key);
        if (existing) {
            if (!existing.channels.includes(row.notificationType)) {
                existing.channels.push(row.notificationType);
            }
            continue;
        }

        const comedianName = row.comedian?.name ?? "A comedian you follow";
        const club = row.show?.club;
        const clubName = club?.name ?? "";
        const location = [club?.city, club?.state]
            .filter(Boolean)
            .join(", ");

        groups.set(key, {
            id: key,
            title: `${comedianName} is performing near you`,
            // Join only the non-empty segments so a missing club name (or
            // missing location) never leaves a dangling " · " separator.
            body: [clubName, location].filter(Boolean).join(" · "),
            comedianId: row.comedianId,
            comedianName,
            showId: row.showId,
            showPageUrl: row.show?.showPageUrl ?? null,
            showDate: row.show?.date ? row.show.date.toISOString() : null,
            clubName: clubName || null,
            city: club?.city ?? null,
            state: club?.state ?? null,
            channels: [row.notificationType],
            sentAt: row.sentAt.toISOString(),
            // A group is unread when its most recent send (the first row, since
            // rows are sorted desc) is newer than the last-seen high-water mark.
            isUnread: lastSeenAt ? row.sentAt > lastSeenAt : true,
        });
    }

    const items = Array.from(groups.values());
    const unreadCount = items.filter((item) => item.isUnread).length;

    return NextResponse.json(
        {
            data: {
                items,
                unreadCount,
                lastSeenAt: lastSeenAt ? lastSeenAt.toISOString() : null,
            },
        },
        { headers: rateLimitHeaders(rl) },
    );
});

export const PATCH = withRequestMetrics(async function PATCH(req: NextRequest) {
    const ipRl = await checkRateLimit(
        `me-notifications-ip:${getClientIp(req)}`,
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
        `me-notifications:${authCtx.userId}`,
        RATE_LIMITS.authenticated,
    );
    if (!rl.allowed) return rateLimitResponse(rl);

    let body: unknown;
    try {
        body = await req.json();
    } catch {
        return NextResponse.json(
            { error: "Invalid JSON body" },
            { status: 400 },
        );
    }

    const parsed = NotificationPreferenceUpdateSchema.safeParse(body);
    if (!parsed.success) {
        return NextResponse.json(
            { error: parsed.error.errors[0].message },
            { status: 400 },
        );
    }

    const updatedProfile = await db.userProfile.update({
        where: { userid: authCtx.userId },
        data: {
            emailShowNotifications: parsed.data.emailShowNotifications,
            pushShowNotifications: parsed.data.pushShowNotifications,
        },
        select: {
            emailShowNotifications: true,
            pushShowNotifications: true,
        },
    });

    return NextResponse.json({
        data: {
            emailShowNotifications: updatedProfile.emailShowNotifications,
            pushShowNotifications: updatedProfile.pushShowNotifications,
        },
    });
});
