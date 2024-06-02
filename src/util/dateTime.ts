import { HTMLConfigurable } from "../types/configs.interface.js";
import moment from 'moment-timezone';

export const combineDateAndTimeStrings = (showDateString: string, showTimeString: string, config: HTMLConfigurable): Date => {


    const cleanedDateString = cleanDateString(showDateString, config);
    const cleanedTimeString = cleanTimeString(showTimeString, config);

    const dateTimeStr = `${cleanedDateString}/${cleanedTimeString}`;

    const [dateComponents, timeComponents] = dateTimeStr.split('/');
    
    // Extract time components
    const [hours, minutesAndMeridiem] = timeComponents.split(':');
    const [minutes, meridiem] = minutesAndMeridiem.split(' ');

    // Adjust hours for PM
    const adjustedHours = parseInt(hours) + (meridiem.match('PM') ? 12 : 0);
    
     // Format date string
    const formattedDateString = `${dateComponents} ${adjustedHours}:${minutes}:00`;
  
    return new Date(formattedDateString);
}

export const stringIsDateTime = (inputString: string): boolean => {
    return /^\d{4}-\d{2}-\d{2} \d{2}:\d{2} [AP]M$/.test(inputString);
}


export const cleanDateString = (dateString: string, config: HTMLConfigurable): string => {
    if (stringIsDateTime(dateString)) {
        return dateString;
    }
    return dateString.replace(config.extraDateString, '');
}


export const cleanTimeString = (timeString: string, config: HTMLConfigurable): string => {
    if (stringIsDateTime(timeString)) {
        return timeString;
    }
    return timeString.replace(config.extraTimeString, '').toUpperCase();
}

export const convertDatetimeToLocalTimezone = (dateTime: Date, timezone: string): string => {
    return moment(dateTime).tz(timezone).format();
}

export const addDelay = (time: number) => {
    return new Promise(function(resolve) { 
        setTimeout(resolve, time)
    });
  }