import { ClubConfig } from "../types/index.js";
import moment from 'moment-timezone';

export const combineDateAndTimeStrings = (showDateString: string, showTimeString: string, clubConfig: ClubConfig): Date => {


    const cleanedDateString = cleanDateString(showDateString, clubConfig);
    const cleanedTimeString = cleanTimeString(showTimeString, clubConfig);

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


export const cleanDateString = (dateString: string, clubConfig: ClubConfig): string => {
    if (stringIsDateTime(dateString)) {
        return dateString;
    }
    return dateString.replace(clubConfig.textConfig.extraDateString, '');
}


export const cleanTimeString = (timeString: string, clubConfig: ClubConfig): string => {
    if (stringIsDateTime(timeString)) {
        return timeString;
    }
    return timeString.replace(clubConfig.textConfig.extraTimeString, '').toUpperCase();
}

export const convertDatetimeToLocalTimezone = (dateTime: Date, clubConfig: ClubConfig): string => {
    return moment(dateTime).tz(clubConfig.timezone).format();
}

export const addDelay = (time: number) => {
    return new Promise(function(resolve) { 
        setTimeout(resolve, time)
    });
  }