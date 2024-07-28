import { DATE } from "../../constants/dateConstants.js";
import { REGEX } from "../../constants/regex.js";
import { ShowHTMLConfiguration } from "../../types/htmlconfigurable.interface.js";
import { removeBadWhiteSpace, removeSubstrings } from "./stringUtil.js";

export const cleanDateString = (dateString: string, config: ShowHTMLConfiguration): string => {
    const badStringString = config.badDateStrings?.concat(DATE.days, DATE.ordinals)
    const cleanedString = removeSubstrings(dateString, badStringString)
    return removeBadWhiteSpace(cleanedString)
}

export const cleanTimeString = (timeString: string, config: ShowHTMLConfiguration): string => {
    const cleanedString = removeSubstrings(timeString, config.badTimeStrings)
    return removeBadWhiteSpace(cleanedString)
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

export const extractDateUsingRegex = (dateString: string): string =>  {
    const dateValues = dateString.match(REGEX.dateWithSlash) ?? [];
    return dateValues[0] as string
}

export const normalizeDateString = (dateString: string) => {
    const validDate = geenrateValidDateString(dateString);

    const dateObject = new Date(validDate);
    const year = dateObject.getFullYear();
    const month = dateObject.getMonth() + 1;
    const day = dateObject.getDate();

    return year.toString() + "-" + month.toString() + "-" + day.toString();
}

const addDateValues = (dateString: string) => {
    return dateString + " 2024"
}

const geenrateValidDateString = (dateString: string): string => {    
    var regexDate = extractDateUsingRegex(dateString);
    var completeDate = addDateValues(dateString);

    if (stringIsAValidDate(dateString)) return dateString
    else if (stringIsAValidDate(regexDate)) return regexDate
    else if (stringIsAValidDate(completeDate)) return completeDate

    throw new Error(`Can't turn ${dateString} into a date`)
}

