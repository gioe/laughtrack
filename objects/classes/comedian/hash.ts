import { Md5 } from "ts-md5";
import { removeNonAlphanumeric } from "../../../util/primatives/stringUtil";

export const generateComedianHash = (name: string): string => {
    const cleanedString = removeNonAlphanumeric(name).toLocaleLowerCase();
    return Md5.hashStr(cleanedString);
};
