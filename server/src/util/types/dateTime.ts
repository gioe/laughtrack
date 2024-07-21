import { REGEX } from '../../constants/regex.js';
import { removeBadWhiteSpace, removeSubstrings, replaceSubstrings } from './stringUtil.js';
import { ShowHTMLConfiguration } from '../../types/htmlconfigurable.interface.js';
import moment from 'moment';

const cleanDateTime = (dateTime: string, badStrings?: string[]) => {
    const noWhiteSpaceString = removeBadWhiteSpace(dateTime)
    return removeSubstrings(noWhiteSpaceString, badStrings)
}

export const normalizeDateTime = (dateTime: string, config: ShowHTMLConfiguration) => {
    const cleanedDateTime = cleanDateTime(dateTime, config.badTimeStrings)
    const normalizedDateString = extractDateFromDateTime(cleanedDateTime)
    const normalizedTimeString = exactTimeFromDateTime(cleanedDateTime)

    return normalizedDateString + "T" + normalizedTimeString
}

export const extractDateFromDateTime = (inputString: string): string => {

    var dateString = inputString

    const dateValues = inputString.match(REGEX.dateWithSlash) ?? [];

    if (stringIsAValidDate(inputString)) dateString = inputString
    else if (dateValues.length > 0) dateString = getDateFromRegexMatch(dateValues)

    return normalizeDateString(dateString)

}

export const exactTimeFromDateTime = (inputString: string): string => {
    var timeString = ""
    const meridiem = inputString.includes('p') ? "pm" : "am"

    const timeValues = inputString.match(REGEX.time) ?? [];

    if (timeValues.length > 0) timeString = timeValues[0] as string
    return normalizeTimeString(timeString, meridiem)
}


export const normalizeDateString = (dateString: string) => {
    const dateObject = new Date(dateString);
    const year = dateObject.getFullYear();
    const month = dateObject.getMonth() + 1;
    const day = dateObject.getDate();

    return year.toString() + "-" + month.toString() + "-" + day.toString();
}

export const normalizeTimeString = (time: string, meridiem: string) => {
    const [hours, minutes] = time.split(':');
    const adjustedHours = parseInt(hours) + (meridiem.includes('p') ? 12 : 0);
    return `${adjustedHours}:${minutes}:00`;
}

const stringIsAValidDate = (string: string): boolean => {
    var date = Date.parse(string);
    return isNaN(date) ? false : true
}

const getDateFromRegexMatch = (regexMatchArray: RegExpMatchArray | []): string =>  {
    const dateString = regexMatchArray[0] as string
    if (dateString != undefined && stringIsAValidDate(dateString)) {
        return dateString
    } 
    return ""
}

export const createDate = (dateTimeString: string, timeZone: string) => {
    const [date, time] = dateTimeString.split('T');
    const [hours, minutes, seconds] = time.split(':');

    const newDate = new Date(date)
    newDate.setHours(Number(hours))
    newDate.setMinutes(Number(minutes))
    newDate.setSeconds(Number(seconds))
    
    return newDate;
}