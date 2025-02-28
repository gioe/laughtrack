import { DateRange } from "@/objects/interface";
import { format, isToday, isTomorrow, isSameDay } from "date-fns";

// Types
type DateFormatter = (date: Date) => string;

// Constants
const DEFAULT_DATE_FORMAT = "LLL d, yyyy";

/**
 * Formats a single date with special handling for today and tomorrow
 */
const formatSingleDate: DateFormatter = (date: Date): string => {
    if (isToday(date)) return "Today - ";
    if (isTomorrow(date)) return "Tomorrow - ";
    return `${format(date, DEFAULT_DATE_FORMAT)} - `;
};

/**
 * Checks if a date range spans a single day
 */
const isSingleDayRange = (from: Date, to: Date): boolean => {
    return isSameDay(from, to);
};

/**
 * Formats a date range as a string
 */
export const formatDateRange = (placeholder: string, range: DateRange): string => {
    // Handle undefined or empty range
    if (!range?.to && !range?.from) {
        return placeholder;
    }

    const { from, to } = range;

    try {
        // Handle single date selection
        if (!to && from) {
            return formatSingleDate(from);
        }

        // Handle invalid range where only 'to' date exists
        if (to && !from) {
            return formatSingleDate(to);
        }

        // At this point, both from and to should exist
        if (!from || !to) {
            throw new Error("Invalid date range");
        }

        // Handle single day range
        if (isSingleDayRange(from, to)) {
            return formatSingleDate(from);
        }

        // Handle multi-day range
        return `${formatSingleDate(from)} ${format(to, DEFAULT_DATE_FORMAT)}`;

    } catch (error) {
        console.error("Error formatting date range:", error);
        return placeholder;
    }
};

export const parseToMidnight = (value: string | null): Date | undefined => {
    const dateTime = `${value}T00:00:00`
    const date = value ? new Date(dateTime) : new Date("");

    // If the date is invalid, return undefined
    if (isNaN(date.getTime())) return undefined;

    // Set the time to midnight (00:00:00) in the local timezone
    date.setHours(0, 0, 0, 0);
    return date;
};
export const isDateTodayOrLater = (value: Date | undefined): boolean => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return value == undefined || value >= today;
};
