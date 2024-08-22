import { ScrapingConfig } from "../classes/ScrapingConfig.js";
import { DATE } from "../constants/dateConstants.js";
import { REGEX } from "../constants/regex.js";
import { removeNonNumbers, removeSubstrings } from "./stringUtil.js";

var months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

export const normalizeDateString = (dateString: string, config: ScrapingConfig): string => {
    const cleanedDateString = cleanDateString(dateString, config)
    if (stringIsAValidDate(cleanedDateString)) return cleanedDateString
    else {
        const regexDate = getDateByRegex(cleanedDateString);
        return regexDate ? regexDate: cleanedDateString;
    }
}

export const cleanDateString = (dateString: string, config: ScrapingConfig): string => {
    const badDateContent = getBadDateStringContent(config)
    return removeSubstrings(dateString, badDateContent)
}

const getBadDateStringContent = (config: ScrapingConfig) => {
    var badContent: string[] = config.badDateStrings ?? []
    badContent = badContent.concat(DATE.days);
    return badContent
}

export const stringIsAValidDate = (string: string): boolean => {
    if (string == undefined) return false
    var date = Date.parse(string);
    return !isNaN(date) 
}

export const getDateByRegex = (dateString: string): string | undefined =>  {
    const dateValues = dateString.match(REGEX.dateRegex);
    return dateValues ? dateValues[0] as string : undefined
}

export const determineDay = (dateString: string): number => {
    const numberString = removeNonNumbers(dateString);
    return Number(numberString)
}

export const determineMonth = (dateString: string): number => {
    var monthIndex = 0;
    months.forEach((month, index) => {
        if (dateString.toLowerCase().includes(month)) {
            monthIndex = index
        }
    })
    return monthIndex;
}

export const determineYear = (month: number): number => {
    const currentDate = new Date()
    return currentDate.getMonth() < month ? currentDate.getFullYear() + 1 : currentDate.getFullYear();
}

