import moment from 'moment-timezone';
import { removeLeadingWhiteSpace } from './stringUtil.js';


export const buildDateFromDateTimeString = (dateTimeString: string): Date => {
    const trimmedString = removeLeadingWhiteSpace(dateTimeString)
    const [day, date, month, dateComponents, timeComponents, meridiem] = trimmedString.split(' ');
    return buildDateFromDateAndTimeStrings(dateComponents, timeComponents, meridiem)
}

export const buildDateFromDateAndTimeStrings = (dateString: string, timeString: string, meridiem: string): Date => {    
    // // Extract time components
    const [hours, minutes] = timeString.split(':');

    // Adjust hours for PM
    const adjustedHours = parseInt(hours) + (meridiem.includes('p') ? 12 : 0);
    
     // Format date string
    const formattedDateString = `${dateString} ${adjustedHours}:${minutes}:00`;
    
    return new Date(formattedDateString);;
}


export const stringIsDateTime = (inputString: string): boolean => {
    return /^\d{4}-\d{2}-\d{2} \d{2}:\d{2} [AP]M$/.test(inputString);
}

export const convertDatetimeToString = (dateTime: Date): string => {
    return moment(dateTime).format();
}

export const addDelay = (time: number) => {
    return new Promise(function(resolve) { 
        setTimeout(resolve, time)
    });
  }