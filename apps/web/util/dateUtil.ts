import { formatInTimeZone, toZonedTime } from "date-fns-tz";

// Clubs without a populated timezone column fall back to ET (matching the scraper's
// default in apps/scraper/src/laughtrack/core/entities/club/model.py:27).
export const DEFAULT_SHOW_TIMEZONE = "America/New_York";

// Presentation compatibility for clients whose ICU predates IANA 2026b/2026c.
// These legal boundaries precede the first skipped autumn clock change. Keep
// historical instants on their original IANA rules and store no adjusted dates.
// Aliases are IANA links, not guesses based on province or geographic proximity.
const PERMANENT_SHOW_TIME = [
    {
        zones: ["America/Edmonton", "Canada/Mountain"],
        since: Date.parse("2026-06-18T06:00:00Z"),
        offsetHours: -6,
        label: "ABT",
    },
    {
        zones: ["America/Vancouver", "Canada/Pacific"],
        since: Date.parse("2026-03-09T07:00:00Z"),
        offsetHours: -7,
        label: "PT",
    },
] as const;

export function formatShowDate(
    dateString: string,
    timezone?: string | null,
): string {
    const date = new Date(dateString);
    const tz = timezone || DEFAULT_SHOW_TIMEZONE;

    const permanentTime = PERMANENT_SHOW_TIME.find(
        (rule) =>
            rule.zones.some((zone) => zone === tz) &&
            date.getTime() >= rule.since,
    );
    // Fixed-rule wall fields use UTC accessors: neither the host timezone nor
    // stale browser ICU can change them. Other dates retain the existing Intl
    // path; toZonedTime exposes their venue wall time through local accessors.
    const zoned = permanentTime
        ? new Date(date.getTime() + permanentTime.offsetHours * 60 * 60 * 1000)
        : toZonedTime(date, tz);

    const months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ];
    const month =
        months[permanentTime ? zoned.getUTCMonth() : zoned.getMonth()];
    const day = permanentTime ? zoned.getUTCDate() : zoned.getDate();
    const suffix = getDaySuffix(day);

    const hours = permanentTime ? zoned.getUTCHours() : zoned.getHours();
    const minutes = permanentTime ? zoned.getUTCMinutes() : zoned.getMinutes();
    const period = hours >= 12 ? "pm" : "am";
    const displayHours = hours % 12 || 12;
    const displayMinutes = minutes.toString().padStart(2, "0");

    // Government-facing labels remain stable across ICU versions, which may
    // variously call the new fixed offsets MDT/CST and PDT/MST.
    const tzLabel = permanentTime?.label ?? formatInTimeZone(date, tz, "zzz");

    return `${month} ${day}${suffix} at ${displayHours}:${displayMinutes} ${period} ${tzLabel}`;
}

// "Happening now" window: show is treated as live from start time through this many
// hours after. 2.5h covers a typical standup show with buffer for late starts.
const LIVE_WINDOW_HOURS = 2.5;

export type ShowCountdownTone = "future" | "live" | "past";

export interface ShowCountdown {
    label: string;
    tone: ShowCountdownTone;
}

export function formatShowCountdown(
    dateString: string,
    now: Date = new Date(),
): ShowCountdown {
    const showTime = new Date(dateString).getTime();
    const nowTime = now.getTime();
    const diffMs = showTime - nowTime;
    const liveWindowMs = LIVE_WINDOW_HOURS * 60 * 60 * 1000;

    if (diffMs <= 0 && diffMs > -liveWindowMs) {
        return { label: "Happening now", tone: "live" };
    }

    if (diffMs > 0) {
        return { label: `Show in ${relativeFuture(diffMs)}`, tone: "future" };
    }

    return { label: `Ended ${relativePast(-diffMs)} ago`, tone: "past" };
}

export function isShowPast(
    dateString: string,
    now: Date = new Date(),
): boolean {
    return formatShowCountdown(dateString, now).tone === "past";
}

// Floor for both directions so the unit only flips when the boundary is crossed
// (e.g. 119 min → "1 hour", 120 min → "2 hours") and so a 14-month-out show and
// a 14-month-ago show render symmetrically.
function relativeFuture(ms: number): string {
    const minutes = Math.floor(ms / (60 * 1000));
    if (minutes < 60) {
        return `${minutes} ${minutes === 1 ? "minute" : "minutes"}`;
    }
    const hours = Math.floor(ms / (60 * 60 * 1000));
    if (hours < 24) {
        return `${hours} ${hours === 1 ? "hour" : "hours"}`;
    }
    const days = Math.floor(ms / (24 * 60 * 60 * 1000));
    if (days < 14) {
        return `${days} ${days === 1 ? "day" : "days"}`;
    }
    const weeks = Math.floor(days / 7);
    if (weeks < 9) {
        return `${weeks} ${weeks === 1 ? "week" : "weeks"}`;
    }
    const months = Math.floor(days / 30);
    if (months < 12) {
        return `${months} ${months === 1 ? "month" : "months"}`;
    }
    const years = Math.floor(days / 365);
    return `${years} ${years === 1 ? "year" : "years"}`;
}

function relativePast(ms: number): string {
    const minutes = Math.floor(ms / (60 * 1000));
    if (minutes < 60) {
        return `${minutes} ${minutes === 1 ? "minute" : "minutes"}`;
    }
    const hours = Math.floor(ms / (60 * 60 * 1000));
    if (hours < 24) {
        return `${hours} ${hours === 1 ? "hour" : "hours"}`;
    }
    const days = Math.floor(ms / (24 * 60 * 60 * 1000));
    if (days < 14) {
        return `${days} ${days === 1 ? "day" : "days"}`;
    }
    const weeks = Math.floor(days / 7);
    if (weeks < 9) {
        return `${weeks} ${weeks === 1 ? "week" : "weeks"}`;
    }
    const months = Math.floor(days / 30);
    if (months < 12) {
        return `${months} ${months === 1 ? "month" : "months"}`;
    }
    const years = Math.floor(days / 365);
    return `${years} ${years === 1 ? "year" : "years"}`;
}

function getDaySuffix(day: number): string {
    if (day >= 11 && day <= 13) {
        return "th";
    }

    switch (day % 10) {
        case 1:
            return "st";
        case 2:
            return "nd";
        case 3:
            return "rd";
        default:
            return "th";
    }
}
