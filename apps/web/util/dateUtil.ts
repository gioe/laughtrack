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
