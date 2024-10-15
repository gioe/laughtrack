import { REGEX } from "./constants/regex.js";

export const getTimeByRegex = (timeString: string): string =>  {
    const timeValues = timeString.match(REGEX.time) ?? [];
    return timeValues[0] ?? "";
}

export const getMeridiemByRegex = (timeString: string): string =>  {
    const timeValues = timeString.match(REGEX.meridiem) ?? [];
    return timeValues[0] ?? "";
}
