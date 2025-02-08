import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { QueryProperty } from "@/objects/enum";

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
        return undefined;
     }

    return { from, to };
};


export const getDistanceDataFromParams = (paramsHelper: SearchParamsHelper): DistanceData | undefined => {
    const distance = paramsHelper.getParamValue(QueryProperty.Distance) as string;
    const zipCode = paramsHelper.getParamValue(QueryProperty.Zip) as string;

    if (!distance && !zipCode) {
        return undefined;
     }

    return { distance, zipCode };
};
