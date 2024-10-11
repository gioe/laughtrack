import { REGEX } from "./constants/regex.js";
import { ScrapingConfig } from "../models/classes/ScrapingConfig.js";
import { removeSubstrings } from "./primatives/stringUtil.js";

export const normalizeTimeString = (timeString: string, meridiem: string, config: ScrapingConfig) => {
    const cleanedTimeString = cleanTimeString(timeString, config)
    const determinedMeridiem = determineMeridiem(cleanedTimeString, meridiem);

    const numericString = removeSubstrings(cleanedTimeString, [determinedMeridiem, determinedMeridiem.toLowerCase()])

    var [hours, minutes] = numericString.split(':');

    if (parseInt(hours) == 12) {
        hours = "00"
    }
    
    const adjustedHours = parseInt(hours) + (determinedMeridiem == 'PM' ? 12 : 0);

    return minutes === undefined ? `${adjustedHours}:00` : `${adjustedHours}:${minutes}`;
}

const determineMeridiem = (timeString: string, meridiem: string): string => {
    if (timeString.toLowerCase().includes('pm') || meridiem.toLowerCase() == 'pm' || meridiem.length == 0) {
        return "PM"
    }
    return "AM"
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
