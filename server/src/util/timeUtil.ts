import { ScrapingConfig } from "../classes/ScrapingConfig.js";
import { REGEX } from "../constants/regex.js";
import { removeSubstrings } from "./stringUtil.js";

export const normalizeTimeString = (timeString: string, config: ScrapingConfig) => {
    const cleanedTimeString = cleanTimeString(timeString, config)

    const meridiem = cleanedTimeString.toLowerCase().includes('pm') ? "PM" : "AM"

    const numericString = removeSubstrings(cleanedTimeString, [meridiem, meridiem.toLowerCase()])

    const [hours, minutes] = numericString.split(':');

    const adjustedHours = parseInt(hours) + (meridiem == 'PM' ? 12 : 0);

    return minutes === undefined ? `${adjustedHours}:00` : `${adjustedHours}:${minutes}`;
}


export const cleanTimeString = (timeString: string, config: ScrapingConfig): string => {
    const badTimeContent = getBadTimeStringContent(config)
    return removeSubstrings(timeString, badTimeContent)
}

const getBadTimeStringContent = (config: ScrapingConfig) => {
    var badContent: string[] = config.badTimeStrings ?? [] 
    return badContent
}

export const getTimeByRegex = (timeString: string): string =>  {
    const timeValues = timeString.match(REGEX.time) ?? [];
    return timeValues[0] ?? "";
}
