import { ShowHTMLConfiguration } from '../../types/htmlconfigurable.interface.js';
import { cleanDateString, normalizeDateString, stringIsAValidDate } from './dateUtil.js';
import { cleanTimeString, getTimeByRegex, normalizeTimeString, stringIsAValidTime } from './timeUtil.js';

export const normalizeDateTime = (dateTime: string, config: ShowHTMLConfiguration) => {
    const timeValue = getTimeByRegex(dateTime)

    // We passed in the date and time together no matter what.
    // The time value will be the most straightforward to find so split by the time value itself in order to get the two
    // strings
    if (timeValue) {
        var dateString = dateTime.split(timeValue)[0]
        var timeString = timeValue + dateTime.split(timeValue)[1]

        dateString = normalizeDateIfNecessary(dateString, config)
        timeString = normalizeTimeIfNecessary(timeString, config)

        return dateString + "T" + timeString
    }
    
    throw new Error(`${dateTime} doesn't have a time to separate on`)

}

export const normalizeDateIfNecessary = (dateString: string, config: ShowHTMLConfiguration): string => {
    const cleanedDateString = cleanDateString(dateString, config)
    if (stringIsAValidDate(dateString)) return dateString
    else return normalizeDateString(cleanedDateString)
}

export const normalizeTimeIfNecessary = (timeString: string, config: ShowHTMLConfiguration): string => {
    const cleanedTimeString = cleanTimeString(timeString, config)
    if (stringIsAValidTime(cleanedTimeString)) return cleanedTimeString
    else return normalizeTimeString(cleanedTimeString)
}

export const createDateObject = (dateTimeString: string, timeZone: string) => {
    const [date, time] = dateTimeString.split('T');
    const [hours, minutes] = time.split(':');

    const newDate = new Date(date)
    
    newDate.setHours(Number(hours))
    newDate.setMinutes(Number(minutes))

    return newDate;
}