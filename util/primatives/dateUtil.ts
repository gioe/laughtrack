import {
    removeNonNumbers,
} from "./stringUtil";

export const determineDate = (dateString: string): number => {
    const numberString = removeNonNumbers(dateString);
    return Number(numberString);
};
