import { REGEX } from "../../constants/regex.js";
import { removeSubstrings } from "./stringUtil.js";

export const stringIsAValidTime = (string: string): boolean => {
    const [hourString, minuteString] = string.split(':');
    const hours = Number(hourString)
    const minutes = Number(minuteString)

   // If after parsing the string it is NaN, that means it's an invalid time.
   return !isNaN(hours) && !isNaN(minutes) && !includesMeridiem(string)
}

export const checkHourByMeridiem = (hour: number, meridiem: string): boolean => {
    return meridiem === "PM" ? hour >= 12 : hour < 12
} 

export const includesMeridiem = (timeString: string): boolean => {
    return timeString.toLowerCase().includes('pm') || timeString.toLowerCase().includes('am')
} 

export const getMeridiem = (timeString: string): string => {
    return timeString.toLowerCase().includes('pm') ? "PM" : "AM"
} 

export const getTimeByRegex = (timeString: string): string | undefined =>  {
    const timeValues = timeString.match(REGEX.time) ?? [];
    return timeValues[0];
}

export const normalizeTimeString = (time: string) => {
    const meridiem = getMeridiem(time)
    const numericString = removeSubstrings(time, [meridiem])

    const [hours, minutes] = numericString.split(':');

    const adjustedHours = parseInt(hours) + (meridiem == 'PM' ? 12 : 0);

    return minutes === undefined ? `${adjustedHours}:00` : `${adjustedHours}:${minutes}`;

}

export const adjustTimeString = (time: string) => {
    const [hours, minutes] = time.split(':');
    const adjustedHours = parseInt(hours) + (time.includes('p') ? 12 : 0);
    return `${adjustedHours}:${minutes}`;
}