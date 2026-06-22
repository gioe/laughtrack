"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Bell, ChevronRight } from "lucide-react";

interface NotificationItem {
    id: string;
    title: string;
    body: string;
    showId: number;
    channels: string[];
    sentAt: string;
    isUnread: boolean;
}

interface NotificationCenterTabProps {
    /** Called after the feed loads and is marked seen, so the parent can clear
     * the unread badge. Pass a stable (memoized) callback. */
    onSeen?: () => void;
}

const relativeTime = (iso: string): string => {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    const seconds = Math.round((Date.now() - date.getTime()) / 1000);
    const ranges: [number, Intl.RelativeTimeFormatUnit][] = [
        [60, "second"],
        [3600, "minute"],
        [86400, "hour"],
        [604800, "day"],
        [2629800, "week"],
        [31557600, "month"],
        [Infinity, "year"],
    ];
    const divisors = [1, 60, 3600, 86400, 604800, 2629800, 31557600];
    const formatter = new Intl.RelativeTimeFormat(undefined, {
        numeric: "auto",
        style: "short",
    });
    for (let i = 0; i < ranges.length; i++) {
        if (Math.abs(seconds) < ranges[i][0]) {
            return formatter.format(
                -Math.round(seconds / divisors[i]),
                ranges[i][1],
            );
        }
    }
    return "";
};

/**
 * Web mirror of the iOS notification center. Lists the comedian-arrival
 * notification history from GET /api/v1/me/notifications (cookie-authenticated
 * via resolveAuth), marks everything seen on view (clearing the unread badge),
 * and links each row to the show detail page. Capped server-side at the 100
 * most-recent — a bounded list, not infinite scroll.
 */
const NotificationCenterTab = ({ onSeen }: NotificationCenterTabProps) => {
    const [items, setItems] = useState<NotificationItem[] | null>(null);
    const [error, setError] = useState(false);

    useEffect(() => {
        let cancelled = false;

        const load = async () => {
            try {
                const res = await fetch("/api/v1/me/notifications", {
                    credentials: "same-origin",
                });
                if (!res.ok) throw new Error(`status ${res.status}`);
                const body = await res.json();
                if (cancelled) return;
                setItems((body?.data?.items ?? []) as NotificationItem[]);

                // Opening the center is the "seen" signal: stamp the high-water
                // mark, then clear the parent unread badge.
                try {
                    await fetch("/api/v1/me/notifications/seen", {
                        method: "POST",
                        credentials: "same-origin",
                    });
                    if (!cancelled) onSeen?.();
                } catch {
                    // Non-fatal: the list still renders if mark-seen fails.
                }
            } catch {
                if (!cancelled) setError(true);
            }
        };

        void load();
        return () => {
            cancelled = true;
        };
    }, [onSeen]);

    return (
        <div className="bg-surface-elevated border border-subtle rounded-card p-6 shadow-card">
            <h3 className="text-lg font-semibold mb-4">Notifications</h3>

            {error && (
                <p className="text-muted-foreground font-dmSans">
                    We couldn&apos;t load your notifications. Please try again.
                </p>
            )}

            {!error && items === null && (
                <p className="text-muted-foreground font-dmSans">Loading…</p>
            )}

            {!error && items !== null && items.length === 0 && (
                <div className="flex flex-col items-center gap-2 py-8 text-center">
                    <Bell className="w-8 h-8 text-muted-foreground" />
                    <p className="text-foreground/85 font-dmSans">
                        No notifications yet
                    </p>
                    <p className="text-muted-foreground text-sm font-dmSans">
                        When a comedian you follow has a show near you, you&apos;ll
                        see it here.
                    </p>
                </div>
            )}

            {!error && items !== null && items.length > 0 && (
                <ul className="space-y-3" data-testid="notification-list">
                    {items.map((item) => (
                        <li key={item.id}>
                            <Link
                                href={`/show/${item.showId}`}
                                className="flex items-start gap-3 bg-surface-muted border border-subtle rounded-lg p-4 hover:shadow-floating transition-all"
                            >
                                <span
                                    aria-hidden
                                    className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                                        item.isUnread
                                            ? "bg-copper"
                                            : "bg-transparent"
                                    }`}
                                />
                                <span className="flex-1 min-w-0">
                                    <span className="block font-semibold text-foreground">
                                        {item.title}
                                    </span>
                                    {item.body && (
                                        <span className="block text-sm text-muted-foreground font-dmSans">
                                            {item.body}
                                        </span>
                                    )}
                                    <span className="mt-1 flex items-center gap-2 text-xs text-muted-foreground font-dmSans">
                                        {item.channels.map((channel) => (
                                            <span
                                                key={channel}
                                                className="uppercase tracking-wide border border-subtle rounded-full px-2 py-0.5"
                                            >
                                                {channel}
                                            </span>
                                        ))}
                                        {relativeTime(item.sentAt) && (
                                            <span>{relativeTime(item.sentAt)}</span>
                                        )}
                                    </span>
                                </span>
                                <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 mt-1" />
                            </Link>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};

export default NotificationCenterTab;
