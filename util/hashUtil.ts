import { Md5 } from "ts-md5";
import { removeNonAlphanumeric } from "./primatives/stringUtil";

export const generateHash = (input: string): string => {
    const normalizedString = removeNonAlphanumeric(input).toLocaleLowerCase()
    return Md5.hashStr(normalizedString);
};
