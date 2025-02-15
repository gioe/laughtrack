import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { QueryProperty } from "@/objects/enum";
import { ReadonlyURLSearchParams } from "next/navigation";

export interface DateRange {
    from: Date;
    to?: Date;
}

export interface DistanceData {
    distance?: string;
    zipCode?: string;
}

export const getDateRangeFromParams = (searchParams: ReadonlyURLSearchParams): DateRange | undefined => {
    const fromString = searchParams.get(QueryProperty.FromDate) as string;
    const toString = searchParams.get(QueryProperty.ToDate) as string;

    const from = new Date(fromString);
    const to = new Date(toString);

    return { from, to: isNaN(to.getTime()) ? undefined : to };
};

export const getDistanceDataFromParams = (searchParams: ReadonlyURLSearchParams): DistanceData | undefined => {
    const distance = searchParams.get(QueryProperty.Distance) as string;
    const zipCode = searchParams.get(QueryProperty.Zip) as string

    if (!distance && !zipCode) {
        return undefined;
     }

    return { distance, zipCode };
};
