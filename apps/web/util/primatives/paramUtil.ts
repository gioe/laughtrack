import { format } from "date-fns";

export const formattedDateParam = (value: Date | undefined) => {
    if (!value) return "";
    // toISOString() shifts to UTC and silently flips the calendar day for any
    // wallclock-local Date picked after the local→UTC boundary (e.g. 10pm PST
    // → next-day UTC). format() reads getFullYear/getMonth/getDate, which are
    // local-TZ accessors, so the emitted yyyy-MM-dd round-trips with
    // parseToMidnight (which parses 'yyyy-MM-ddT00:00:00' as local time).
    return format(value, "yyyy-MM-dd");
};
