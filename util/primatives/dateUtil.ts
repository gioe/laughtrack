import { format, isToday, isTomorrow, isSameDay } from "date-fns";
import { DateRange } from "../search/util";

// Types
type DateFormatter = (date: Date) => string;

// Constants
const DEFAULT_DATE_FORMAT = "LLL d, yyyy";

/**
 * Formats a single date with special handling for today and tomorrow
 */
const formatSingleDate: DateFormatter = (date: Date): string => {
    if (isToday(date)) return "Today";
    if (isTomorrow(date)) return "Tomorrow";
    return format(date, DEFAULT_DATE_FORMAT);
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
export const formatDateRange = (placeholder: string, range?: DateRange): string => {
    // Handle undefined or empty range
    if (!range || (!range.to)) {
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
        return `${formatSingleDate(from)} - ${format(to, DEFAULT_DATE_FORMAT)}`;

    } catch (error) {
        console.error("Error formatting date range:", error);
        return placeholder;
    }
};

/**
 * Validates a date range
 */
export const isValidDateRange = (range: DateRange): boolean => {
    if (!range.from) return false;
    if (range.to && range.from > range.to) return false;
    return true;
};

/**
 * Extracts a number from a date string
 * @deprecated Consider using proper date parsing instead
 */
export const determineDate = (dateString: string): number => {
    if (!dateString) return 0;
    return Number(dateString.replace(/\D/g, "")) || 0;
};
