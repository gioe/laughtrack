import { DATE } from "../constants/dateConstants";
import { REGEX } from "../constants/regex";
import {
    removeNonNumbers,
    removeSubstrings,
    stringIsAValidDate,
} from "./stringUtil";

export const normalizeDateString = (dateString: string): string => {
    const cleanedDateString = cleanDateString(dateString);

    if (stringIsAValidDate(cleanedDateString)) return cleanedDateString;
    else {
        const regexDate = getDateByRegex(cleanedDateString);
        return regexDate ? regexDate : cleanedDateString;
    }
};

export const cleanDateString = (dateString: string): string => {
    const badDateContent = getBadDateStringContent();
    return removeSubstrings(dateString, badDateContent);
};

const getBadDateStringContent = () => {
    let badContent: string[] = ["-", "|", ",", "·"];
    badContent = DATE.days.concat(badContent);
    return badContent;
};

export const getDateByRegex = (dateString: string): string | undefined => {
    const dateValues = dateString.match(REGEX.dateRegex);
    return dateValues ? (dateValues[0] as string) : undefined;
};

export const determineDate = (dateString: string): number => {
    const numberString = removeNonNumbers(dateString);
    return Number(numberString);
};

export const determineMonth = (dateString: string): number => {
    let monthIndex = 0;
    DATE.months.forEach((month, index) => {
        if (dateString.toLowerCase().includes(month)) {
            monthIndex = index;
        }
    });
    return monthIndex;
};

export const determineYear = (month: number): number => {
    const currentDate = new Date();
    return month < currentDate.getMonth()
        ? currentDate.getFullYear() + 1
        : currentDate.getFullYear();
};
