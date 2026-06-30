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
import { buildComedianImageUrls } from "@/lib/data/comedian/imageAssets";
import { DEFAULT_SHOW_TIMEZONE } from "@/util/dateUtil";

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
    comedianImageUrl: string;
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

function formatNotificationTitle(comedianName: string): string {
    return `${comedianName} is performing near you`;
}

function formatNotificationSubtitle({
    clubName,
    showDate,
    timezone,
}: {
    clubName: string;
    showDate: Date | null | undefined;
    timezone?: string | null;
}): string {
    const time = showDate ? formatPerformanceTime(showDate, timezone) : "";
    if (clubName && time) return `${clubName} at ${time}`;
    return clubName || time;
}

function formatPerformanceTime(
    showDate: Date,
    timezone?: string | null,
): string {
    const parts = new Intl.DateTimeFormat("en-US", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
        timeZone: timezone || DEFAULT_SHOW_TIMEZONE,
        timeZoneName: "short",
    }).formatToParts(showDate);
    const getPart = (type: Intl.DateTimeFormatPartTypes) =>
        parts.find((part) => part.type === type)?.value ?? "";
    const hour = getPart("hour");
    const minute = getPart("minute");
    const dayPeriod = getPart("dayPeriod").toLowerCase();
    const timeZoneName = getPart("timeZoneName");

    return [hour && minute ? `${hour}:${minute}` : "", dayPeriod, timeZoneName]
        .filter(Boolean)
        .join(" ");
}

function compareNotificationItems(
    a: NotificationItem,
    b: NotificationItem,
): number {
    const sentDiff = Date.parse(b.sentAt) - Date.parse(a.sentAt);
    if (sentDiff !== 0) return sentDiff;

    if (a.showDate && b.showDate) {
        const showDiff = Date.parse(a.showDate) - Date.parse(b.showDate);
        if (showDiff !== 0) return showDiff;
    } else if (a.showDate) {
        return -1;
    } else if (b.showDate) {
        return 1;
    }

    return a.id.localeCompare(b.id);
}

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
            comedian: {
                select: {
                    name: true,
                    hasImage: true,
                    imageAssets: {
                        where: { isActive: true },
                        orderBy: { publishedAt: "desc" },
                        take: 1,
                        select: {
                            avatarPath: true,
                            heroPath: true,
                            isActive: true,
                        },
                    },
                },
            },
            show: {
                select: {
                    date: true,
                    showPageUrl: true,
                    club: {
                        select: {
                            name: true,
                            city: true,
                            state: true,
                            timezone: true,
                        },
                    },
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
        const comedianImageUrl = row.comedian
            ? buildComedianImageUrls({
                  name: comedianName,
                  hasImage: row.comedian.hasImage,
                  activeAsset: row.comedian.imageAssets?.[0] ?? null,
              }).avatarUrl
            : "";
        const club = row.show?.club;
        const clubName = club?.name ?? "";

        groups.set(key, {
            id: key,
            title: formatNotificationTitle(comedianName),
            body: formatNotificationSubtitle({
                clubName,
                showDate: row.show?.date,
                timezone: club?.timezone,
            }),
            comedianId: row.comedianId,
            comedianName,
            comedianImageUrl,
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

    const items = Array.from(groups.values()).sort(compareNotificationItems);
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
