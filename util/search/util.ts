import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { UserInterface } from "@/objects/class/user/user.interface";
import { QueryProperty } from "@/objects/enum";
import { zip } from "lodash";

export interface DateRange {
    from: Date;
    to?: Date;
}

export interface DistanceData {
    distance?: string;
    zipCode?: string;
}
export const getDateRangeFromParams = (paramsHelper: SearchParamsHelper): DateRange | undefined => {
    const fromString = paramsHelper.getParamValue(QueryProperty.FromDate) as string;
    const toString = paramsHelper.getParamValue(QueryProperty.ToDate) as string;

    const from = new Date(fromString);
    const to = new Date(toString);

    if (isNaN(from.getTime()) && isNaN(to.getTime())) {
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(today.getDate() + 1);

        return { from: today, to: tomorrow };
    }
    return { from, to };
};

export const getDistanceDataFromParams = (paramsHelper: SearchParamsHelper, user?:UserInterface): DistanceData | undefined => {
    const distance = paramsHelper.getParamValue(QueryProperty.Distance) as string;
    const zipParam = paramsHelper.getParamValue(QueryProperty.Zip) as string
    const zipCode = zipParam == "" ? (user?.zipCode ?? "10003") : zipParam
    if (!distance && !zipCode) {
        return undefined;
     }

    return { distance, zipCode };
};
