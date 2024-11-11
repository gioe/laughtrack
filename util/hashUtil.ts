import { Md5 } from "ts-md5";

export const geenrateHash = (input: string): string => {
    return Md5.hashStr(input);
};
