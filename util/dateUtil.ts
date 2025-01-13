import moment from "moment";

export function isToday(date: Date) {
    const today = new Date();
    return date.getDate() === today.getDate() &&
        date.getMonth() === today.getMonth() &&
        date.getFullYear() === today.getFullYear();
}

export function isTomorrow(date: Date) {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1); // Increment tomorrow's date by one day

    return date.getDate() === tomorrow.getDate() &&
        date.getMonth() === tomorrow.getMonth() &&
        date.getFullYear() === tomorrow.getFullYear();
}

export function datesAreSame(date1: Date, date2: Date) {
    return date1.getFullYear() === date2.getFullYear() &&
        date1.getMonth() === date2.getMonth() &&
        date1.getDate() === date2.getDate();
}

export function datesAreToday(date1: Date, date2: Date) {
    return datesAreSame(date1, date2) && isToday(date1)
}

export function datesAreTomorrow(date1: Date, date2: Date) {
    return datesAreSame(date1, date2) && isTomorrow(date1)
}

export function dateWithOrdinalFromMoment(moment: moment.Moment) {
    return moment.format('Do');
}

export function monthFromMoment(moment: moment.Moment) {
    return moment.format('MMM');
}

export function timeFromMoment(moment: moment.Moment) {
    return moment.format('h:mm A');
}

export function formatShowDate(dateString: string): string {
    const date = new Date(dateString)
    // Month formatting
    const months = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];
    const month = months[date.getMonth()];

    // Day formatting with suffix
    const day = date.getDate();
    const suffix = getDaySuffix(day);

    // Time formatting
    const hours = date.getHours();
    const minutes = date.getMinutes();
    const period = hours >= 12 ? 'pm' : 'am';

    // Convert to 12-hour format
    const displayHours = hours % 12 || 12;
    const displayMinutes = minutes.toString().padStart(2, '0');

    return `${month} ${day}${suffix} at ${displayHours}:${displayMinutes} ${period}`;
}

function getDaySuffix(day: number): string {
    if (day >= 11 && day <= 13) {
        return 'th';
    }

    switch (day % 10) {
        case 1: return 'st';
        case 2: return 'nd';
        case 3: return 'rd';
        default: return 'th';
    }
}
