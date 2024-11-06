import { REGEX } from "../constants/regex";

export const getTimeByRegex = (timeString: string): string => {
    const timeValues = timeString.match(REGEX.time) ?? [];
    return timeValues[0] ?? "";
};

export const getMeridiemByRegex = (timeString: string): string => {
    const timeValues = timeString.match(REGEX.meridiem) ?? [];
    return timeValues[0] ?? "PM";
};

export const containsTimeValue = (timeString: string): boolean => {
    return timeString.match(REGEX.time) !== null;
};

export const containsTimeRange = (timeString: string): boolean => {
    return timeString.includes("-");
};
