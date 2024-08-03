import { REGEX } from "../../constants/regex.js";
import { ShowHTMLConfiguration } from "../../types/htmlconfigurable.interface.js";
import { removeBadWhiteSpace, removeSubstrings } from "./stringUtil.js";

export const normalizeTimeString = (timeString: string, config: ShowHTMLConfiguration) => {
    if (!stringIsAValidTime(timeString)) throw new Error(`Invalid time string: ${timeString}`)

    const cleanedTimeString = cleanTimeString(timeString, config)

    const meridiem = cleanedTimeString.toLowerCase().includes('pm') ? "PM" : "AM"

    const numericString = removeSubstrings(cleanedTimeString, [meridiem, meridiem.toLowerCase()])

    const [hours, minutes] = numericString.split(':');

    const adjustedHours = parseInt(hours) + (meridiem == 'PM' ? 12 : 0);

    return minutes === undefined ? `${adjustedHours}:00` : `${adjustedHours}:${minutes}`;
}

export const stringIsAValidTime = (string: string): boolean => {
    const [hourString, minuteString] = string.split(':');
    const hours = Number(hourString)
    const minutes = Number(minuteString)

   // If after parsing the string it is NaN, that means it's an invalid time.
   // If it doesn't contain a meridiem, we'll probably have a hard time knowing the correct adjusted time.
   return !isNaN(hours) && !isNaN(minutes) && includesMeridiem(string)
}

export const cleanTimeString = (timeString: string, config: ShowHTMLConfiguration): string => {
    const badTimeContent = getBadTimeStringContent(config)
    return removeSubstrings(timeString, badTimeContent)
}

const getBadTimeStringContent = (config: ShowHTMLConfiguration) => {
    var badContent: string[] = config.badTimeStrings ?? [] 
    return badContent
}

export const includesMeridiem = (timeString: string): boolean => {
    return timeString.toLowerCase().includes('pm') || timeString.toLowerCase().includes('am')
} 

export const getTimeByRegex = (timeString: string): string =>  {
    const timeValues = timeString.match(REGEX.time) ?? [];
    return timeValues[0] ?? "";
}
