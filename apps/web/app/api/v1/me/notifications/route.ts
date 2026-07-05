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
 * One notification-center entry, mirroring the single push that was sent. Rows
 * of `sent_notifications` written in the same run share a `notificationGroupId`,
 * so one entry can cover multiple shows / comedians (matching the grouped push).
 * The title tiers mirror the scraper push builder; `shows` lists the individual
 * shows for the client to render; `route` says where a tap goes (a single-show
 * entry taps into that show, a grouped entry into the Favorites tab). Legacy
 * rows with no group id fall back to one entry per (comedian, show). Copy is
 * reconstructed at read time from the join rather than persisted.
 */
interface NotificationShow {
    showId: number;
    subtitle: string;
    showPageUrl: string | null;
    showDate: string | null;
    clubName: string | null;
    city: string | null;
    state: string | null;
}

interface NotificationComedian {
    comedianId: string;
    comedianName: string;
    comedianImageUrl: string;
}

interface NotificationItem {
    id: string;
    title: string;
    body: string;
    // Primary (soonest-show) comedian, for the row avatar/label.
    comedianId: string | null;
    comedianName: string;
    comedianImageUrl: string;
    comedians: NotificationComedian[];
    shows: NotificationShow[];
    // "favorites" for a grouped entry (tap → Favorites tab); null for a
    // single-show entry (tap → shows[0]). Mirrors the push route key.
    route: string | null;
    channels: string[];
    sentAt: string;
    isUnread: boolean;
}

// Mirrors the scraper _format_comedian_names / _is_plural_comedian_label so the
// notification-center title matches the push copy for the same run.
function formatComedianNames(names: string[]): string {
    const cleaned = names.filter(Boolean);
    if (cleaned.length === 0) return "A comedian you follow";
    if (cleaned.length === 1) return cleaned[0];
    if (cleaned.length === 2) return `${cleaned[0]} and ${cleaned[1]}`;
    return `${cleaned.slice(0, -1).join(", ")}, and ${cleaned[cleaned.length - 1]}`;
}

function isPluralComedianLabel(name: string): boolean {
    return name.includes(" and ") || name.includes(", ");
}

/**
 * Title tiers, matching the push:
 *  - 1 show                 -> "{joined comedians} is/are performing near you"
 *  - >1 show, 1 comedian    -> "{comedian} has N shows near you"
 *  - >1 show, >=2 comedians -> "K comedians you follow have shows near you"
 */
function buildGroupTitle(comedianNames: string[], showCount: number): string {
    if (showCount <= 1) {
        const label = formatComedianNames(comedianNames);
        const verb = isPluralComedianLabel(label) ? "are" : "is";
        return `${label} ${verb} performing near you`;
    }
    if (comedianNames.length <= 1) {
        const name = comedianNames[0] ?? "A comedian you follow";
        const verb = isPluralComedianLabel(name) ? "have" : "has";
        return `${name} ${verb} ${showCount} shows near you`;
    }
    return `${comedianNames.length} comedians you follow have shows near you`;
}

// Compact venue summary line for a grouped entry (the full list lives on the
// Favorites tab the entry taps into): up to two distinct clubs, then "+N more".
function summarizeShowVenues(shows: NotificationShow[]): string {
    const clubs: string[] = [];
    for (const show of shows) {
        if (show.clubName && !clubs.includes(show.clubName)) {
            clubs.push(show.clubName);
        }
    }
    if (clubs.length === 0) return `${shows.length} shows near you`;
    const shown = clubs.slice(0, 2).join(", ");
    const remaining = clubs.length - Math.min(clubs.length, 2);
    return remaining > 0 ? `${shown} + ${remaining} more` : shown;
}

// Cap the history fetch so a long-tenured user with thousands of sent
// notifications never triggers an unbounded query + join payload on every load
// of the notification center. The cap counts pre-grouping rows; email+push for
// the same event collapse afterward, so the rendered item count can be lower.
const NOTIFICATIONS_FETCH_LIMIT = 100;

function formatNotificationSubtitle({
    clubName,
    showDate,
    timezone,
}: {
    clubName: string;
    showDate: Date | null | undefined;
    timezone?: string | null;
}): string {
    const date = showDate ? formatPerformanceDate(showDate, timezone) : "";
    const time = showDate ? formatPerformanceTime(showDate, timezone) : "";
    // "{club} on {date} at {time}", dropping any piece that's missing.
    const when = [date && `on ${date}`, time && `at ${time}`]
        .filter(Boolean)
        .join(" ");
    if (clubName && when) return `${clubName} ${when}`;
    return when || clubName;
}

function formatPerformanceDate(
    showDate: Date,
    timezone?: string | null,
): string {
    // "Friday, July 4" — weekday + full month, club-local. Kept in sync with the
    // scraper push builder (_format_performance_date) so push and in-app copy agree.
    return new Intl.DateTimeFormat("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
        timeZone: timezone || DEFAULT_SHOW_TIMEZONE,
    }).format(showDate);
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

    const aDate = a.shows[0]?.showDate ?? null;
    const bDate = b.shows[0]?.showDate ?? null;
    if (aDate && bDate) {
        const showDiff = Date.parse(aDate) - Date.parse(bDate);
        if (showDiff !== 0) return showDiff;
    } else if (aDate) {
        return -1;
    } else if (bDate) {
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
            notificationGroupId: true,
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

    // Bucket rows into entries. New rows share a notificationGroupId per
    // (user, run) so one entry mirrors the single push that was sent; legacy
    // rows (no group id) fall back to one entry per (comedian, show).
    const groupedRows = new Map<string, typeof rows>();
    for (const row of rows) {
        const key =
            row.notificationGroupId ?? `legacy:${row.comedianId}:${row.showId}`;
        const bucket = groupedRows.get(key);
        if (bucket) bucket.push(row);
        else groupedRows.set(key, [row]);
    }

    const byDateAsc = (a: { date: Date | null }, b: { date: Date | null }) => {
        if (a.date && b.date) return a.date.getTime() - b.date.getTime();
        if (a.date) return -1;
        if (b.date) return 1;
        return 0;
    };

    const items: NotificationItem[] = [];
    for (const [key, groupRows] of groupedRows) {
        // rows are newest-first (query order), so the first carries the entry's
        // sentAt / unread high-water comparison.
        const newestSentAt = groupRows[0].sentAt;
        const channels = new Set<string>();
        const showsById = new Map<
            number,
            { show: NotificationShow; date: Date | null }
        >();
        const comediansById = new Map<
            string,
            { comedian: NotificationComedian; date: Date | null }
        >();

        for (const row of groupRows) {
            channels.add(row.notificationType);
            const comedianName = row.comedian?.name ?? "A comedian you follow";
            const showDate = row.show?.date ?? null;

            if (!comediansById.has(row.comedianId)) {
                const comedianImageUrl = row.comedian
                    ? buildComedianImageUrls({
                          name: comedianName,
                          hasImage: row.comedian.hasImage,
                          activeAsset: row.comedian.imageAssets?.[0] ?? null,
                      }).avatarUrl
                    : "";
                comediansById.set(row.comedianId, {
                    comedian: {
                        comedianId: row.comedianId,
                        comedianName,
                        comedianImageUrl,
                    },
                    date: showDate,
                });
            }

            if (!showsById.has(row.showId)) {
                const club = row.show?.club;
                const clubName = club?.name ?? "";
                showsById.set(row.showId, {
                    date: showDate,
                    show: {
                        showId: row.showId,
                        subtitle: formatNotificationSubtitle({
                            clubName,
                            showDate,
                            timezone: club?.timezone,
                        }),
                        showPageUrl: row.show?.showPageUrl ?? null,
                        showDate: showDate ? showDate.toISOString() : null,
                        clubName: clubName || null,
                        city: club?.city ?? null,
                        state: club?.state ?? null,
                    },
                });
            }
        }

        const shows = Array.from(showsById.values())
            .sort(byDateAsc)
            .map((s) => s.show);
        const comedians = Array.from(comediansById.values())
            .sort(byDateAsc)
            .map((c) => c.comedian);
        const comedianNames = comedians.map((c) => c.comedianName);
        const grouped = shows.length > 1;
        const primary = comedians[0] ?? null;

        items.push({
            id: key,
            title: buildGroupTitle(comedianNames, shows.length),
            // Single-show entry carries the show subtitle; a grouped entry gets a
            // compact venue summary (the full list is on the Favorites tab).
            body: grouped
                ? summarizeShowVenues(shows)
                : (shows[0]?.subtitle ?? ""),
            comedianId: primary?.comedianId ?? null,
            comedianName: primary?.comedianName ?? "A comedian you follow",
            comedianImageUrl: primary?.comedianImageUrl ?? "",
            comedians,
            shows,
            route: grouped ? "favorites" : null,
            channels: Array.from(channels),
            sentAt: newestSentAt.toISOString(),
            isUnread: lastSeenAt ? newestSentAt > lastSeenAt : true,
        });
    }

    items.sort(compareNotificationItems);
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
