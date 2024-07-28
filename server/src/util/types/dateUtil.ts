import { DATE } from "../../constants/dateConstants.js";
import { REGEX } from "../../constants/regex.js";
import { removeBadWhiteSpace, removeSubstrings } from "./stringUtil.js";

const cleanDateString = (dateString: string): string => {
    const cleanedString = removeSubstrings(dateString, DATE.days.concat(DATE.ordinals))
    return removeBadWhiteSpace(cleanedString)
}

export const stringIsAValidDate = (string: string): boolean => {
    if (string !== undefined) {
        const values = string.split(" ")
        var date = Date.parse(string);
    
        // Should be 3 values and the date should be a number
        return values.length == 3 && !isNaN(date) 
    }
    return false
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
    var cleanedDateString = cleanDateString(dateString);

    var regexDate = extractDateUsingRegex(cleanedDateString);
    var completeDate = addDateValues(cleanedDateString);

    if (stringIsAValidDate(cleanedDateString)) return cleanedDateString
    else if (stringIsAValidDate(regexDate)) return regexDate
    else if (stringIsAValidDate(completeDate)) return completeDate

    throw new Error(`Can't turn ${dateString} into a date`)
}

