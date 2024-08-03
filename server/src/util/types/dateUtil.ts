import { DATE } from "../../constants/dateConstants.js";
import { REGEX } from "../../constants/regex.js";
import { ShowHTMLConfiguration } from "../../types/htmlconfigurable.interface.js";
import { removeBadWhiteSpace, removeNonNumbers, removeSubstrings } from "./stringUtil.js";

var months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

export const normalizeDateString = (dateString: string, config: ShowHTMLConfiguration): string => {
    return cleanDateString(dateString, config)
}

export const buildDateObjectIfPossible = (dateString: string): Date | undefined => {    
    var regexDate = getDateByRegex(dateString);

    if (stringIsAValidDate(dateString)) return new Date(dateString);
    else if (stringIsAValidDate(regexDate)) return new Date(regexDate);
    else return undefined;
    
}

export const cleanDateString = (dateString: string, config: ShowHTMLConfiguration): string => {
    const badDateContent = getBadDateStringContent(config)
    const cleanedString = removeSubstrings(dateString, badDateContent)
    return removeBadWhiteSpace(cleanedString)
}

const getBadDateStringContent = (config: ShowHTMLConfiguration) => {
    var badContent: string[] = config.badDateStrings ?? []
    badContent = badContent.concat(DATE.days);
    return badContent
}

export const stringIsAValidDate = (string: string): boolean => {
    if (string == undefined) return false
    const hasThreeValues = checkForValidDateValues(string)
    var date = Date.parse(string);
    return hasThreeValues && !isNaN(date) 
}

const checkForValidDateValues = (string: string): boolean => {
    const values = [" ", "-", "/"]
    .map((separator: string) => string.split(separator))
    .filter((splitValues: string[]) => splitValues.length == 3);
    return values.length > 0
}

export const getDateByRegex = (dateString: string): string =>  {
    const dateValues = dateString.match(REGEX.dateWithSlash) ?? [];
    return dateValues[0] as string
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

