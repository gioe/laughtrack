import { formatInTimeZone, toZonedTime } from "date-fns-tz";

// Clubs without a populated timezone column fall back to ET (matching the scraper's
// default in apps/scraper/src/laughtrack/core/entities/club/model.py:27).
export const DEFAULT_SHOW_TIMEZONE = "America/New_York";

export function formatShowDate(
    dateString: string,
    timezone?: string | null,
): string {
    const date = new Date(dateString);
    const tz = timezone || DEFAULT_SHOW_TIMEZONE;

    // toZonedTime returns a Date whose *local* fields (getMonth/getDate/getHours/...)
    // carry the wallclock time in `tz`. The value is computed from the tz database
    // via Intl, so it's deterministic across server and client regardless of the
    // host system's timezone — no hydration mismatch (cf. hydration error #418).
    const zoned = toZonedTime(date, tz);

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
    const month = months[zoned.getMonth()];
    const day = zoned.getDate();
    const suffix = getDaySuffix(day);

    const hours = zoned.getHours();
    const minutes = zoned.getMinutes();
    const period = hours >= 12 ? "pm" : "am";
    const displayHours = hours % 12 || 12;
    const displayMinutes = minutes.toString().padStart(2, "0");

    const tzLabel = formatInTimeZone(date, tz, "zzz");

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
