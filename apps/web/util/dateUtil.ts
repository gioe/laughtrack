export function isToday(date: Date) {
    const today = new Date();
    return (
        date.getUTCDate() === today.getUTCDate() &&
        date.getUTCMonth() === today.getUTCMonth() &&
        date.getUTCFullYear() === today.getUTCFullYear()
    );
}

export function isTomorrow(date: Date) {
    const tomorrow = new Date();
    tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);

    return (
        date.getUTCDate() === tomorrow.getUTCDate() &&
        date.getUTCMonth() === tomorrow.getUTCMonth() &&
        date.getUTCFullYear() === tomorrow.getUTCFullYear()
    );
}

export function datesAreSame(date1: Date, date2: Date) {
    return (
        date1.getUTCFullYear() === date2.getUTCFullYear() &&
        date1.getUTCMonth() === date2.getUTCMonth() &&
        date1.getUTCDate() === date2.getUTCDate()
    );
}

export function datesAreToday(date1: Date, date2: Date) {
    return datesAreSame(date1, date2) && isToday(date1);
}

export function datesAreTomorrow(date1: Date, date2: Date) {
    return datesAreSame(date1, date2) && isTomorrow(date1);
}

export function formatShowDate(dateString: string): string {
    const date = new Date(dateString);
    // Use UTC methods to avoid server/client timezone mismatch (hydration error #418).
    // Show times are stored as UTC timestamps representing venue-local time.
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
    const month = months[date.getUTCMonth()];

    const day = date.getUTCDate();
    const suffix = getDaySuffix(day);

    const hours = date.getUTCHours();
    const minutes = date.getUTCMinutes();
    const period = hours >= 12 ? "pm" : "am";

    const displayHours = hours % 12 || 12;
    const displayMinutes = minutes.toString().padStart(2, "0");

    return `${month} ${day}${suffix} at ${displayHours}:${displayMinutes} ${period}`;
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
