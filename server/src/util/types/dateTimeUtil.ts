import { removeBadWhiteSpace, removeSubstrings, replaceSubstrings } from './stringUtil.js';
import { ShowHTMLConfiguration } from '../../types/htmlconfigurable.interface.js';
import { normalizeDateString, stringIsAValidDate } from './dateUtil.js';
import { getTimeByRegex, normalizeTimeString, stringIsAValidTime } from './timeUtil.js';

export const normalizeDateTime = (dateTime: string, config: ShowHTMLConfiguration) => {
    const cleanedDateTime = cleanDateTime(dateTime, config.badDateTimeStrings)
    const timeValue = getTimeByRegex(cleanedDateTime)

    var dateString = ""
    var timeString = ""

    // We passed in the date and time together no matter what.
    // The time value will be the most straightforward to find so split by the time value itself in order to get the two
    // strings
    if (timeValue) {
        dateString = cleanedDateTime.split(timeValue)[0]
        timeString = timeValue + cleanedDateTime.split(timeValue)[1]
    }
    
    dateString = normalizeDateIfNecessary(dateString)
    timeString = normalizeTimeIfNecessary(timeString)

    return dateString + "T" + timeString
}

export const normalizeDateIfNecessary = (dateString: string): string => {
    if (stringIsAValidDate(dateString)) return dateString
    else return normalizeDateString(dateString)
}

export const normalizeTimeIfNecessary = (timeString: string): string => {
    if (stringIsAValidTime(timeString)) return timeString
    else return normalizeTimeString(timeString)
}

const cleanDateTime = (dateTime: string, badStrings?: string[]) => {
    const cleanedString = removeSubstrings(dateTime, badStrings)
    return removeBadWhiteSpace(cleanedString)
}

export const createDateObject = (dateTimeString: string, timeZone: string) => {
    const [date, time] = dateTimeString.split('T');
    const [hours, minutes] = time.split(':');

    const newDate = new Date(date)
    
    newDate.setHours(Number(hours))
    newDate.setMinutes(Number(minutes))

    return newDate;
}