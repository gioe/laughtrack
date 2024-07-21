import moment from 'moment-timezone';
import { removeLeadingWhiteSpace, removeSubstrings } from './stringUtil.js';

// export const formatDateTime = (dateTimeString: string): string => {
//     console.log(dateTimeString)
//     const [weekday, date, month, dateComponents, timeComponents, meridiem] = dateTimeString.split(' ');
//     const [componentMonth, componentDate, componentYear] = dateComponents.split('/');    

//     return formatDateComponents(componentYear, componentMonth, componentDate);
// }

// export const formatDate = (dateString: string): string => {
//     const dateMillis = Date.parse(dateString);
//     const dateObject = new Date(dateMillis);

//     var date = dateObject.getDate()
//     var month = dateObject.getMonth() + 1;
//     var year = dateObject.getFullYear();

//     return formatDateComponents(year, month, date);
// }


export const buildDate = (inputString: string, timezone: string): Date => {
    console.log(inputString)
    const [dateComponents, timeComponents, meridiem] = inputString.split(' ');

    // // Extract time components
    const [hours, minutes] = timeComponents.split(':');

    // Adjust hours for PM
    const adjustedHours = parseInt(hours) + (meridiem.includes('p') ? 12 : 0);

    // Format date string
    const formattedDateString = `${dateComponents}T${adjustedHours}:${minutes}:00Z`;

    return moment.tz(formattedDateString, timezone).toDate()
}

export const formatTimeString = (timeString: string) => {
    const [timeComponents, meridiem] = timeString.split(' ');
    const [hours, minutes] = timeComponents.split(':');
    const adjustedHours = parseInt(hours) + (meridiem.includes('p') ? 12 : 0);
    return `${adjustedHours}:${minutes}:00Z`;
}
