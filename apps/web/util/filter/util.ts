import { QueryProperty, SortParamValue } from "@/objects/enum";
import { allDistanceOptions } from "@/objects/enum/distanceValues";
import { allSortOptions } from "@/objects/enum/sortParamValue";
import { SortOptionInterface } from "@/objects/interface";
import { isDateTodayOrLater, parseToMidnight } from "../primatives/dateUtil";
import { formattedDateParam } from "../primatives/paramUtil";

export const getDefaultSortingOption = (
    sortOptions: SortOptionInterface[],
    sortOption: string | null | undefined,
) => {
    // Explicit default: when no sort param is in the URL, use the first option
    // for the entity type (e.g. PopularityDesc for comedians, DateAsc for shows).
    if (!sortOption) return sortOptions[0];
    return (
        sortOptions.find((value) => value.value === sortOption) ??
        sortOptions[0]
    );
};

export const paramsContainsFilter = (
    params: string | null,
    filter: string | null,
): boolean => {
    if (!filter || !params) return false;
    return params.includes(filter);
};

interface ParamConfig<T> {
    key: string;
    defaultValue: T;
    parse: (value: string | null) => T;
    stringify: (value: T) => string;
    validate: (value: T) => boolean;
}

export type ParamTypeMap = {
    page: number;
    size: number;
    sort: SortParamValue;
    comedian: string;
    club: string;
    zip: string;
    distance: string;
    toDate: Date | undefined;
    fromDate: Date | undefined;
    filters: string;
    includeEmpty: boolean;
};

// Centralized parameter configuration
export const paramConfigs: {
    [K in keyof ParamTypeMap]: ParamConfig<ParamTypeMap[K]>;
} = {
    page: {
        key: QueryProperty.Page,
        defaultValue: 1,
        parse: (value: string | null) => {
            const parsed = parseInt(value || "1");
            return parsed > 0 ? parsed : 1;
        },
        stringify: (value: number) => value.toString(),
        validate: (value: number) => value > 0,
    },
    size: {
        key: QueryProperty.Size,
        defaultValue: 10,
        parse: (value: string | null) => {
            const parsed = parseInt(value || "10");
            return parsed > 0 ? parsed : 10;
        },
        stringify: (value: number) => value.toString(),
        validate: (value: number) => value > 0,
    },
    sort: {
        key: QueryProperty.Sort,
        // defaultValue is the "URL clean value": setTypedParam omits the sort param
        // when this value is selected (DateAsc = shows default). Per-entity defaults
        // are resolved by getDefaultSortingOption returning sortOptions[0] when the
        // URL param is absent — see that function for the explicit null-check path.
        defaultValue: SortParamValue.DateAsc,
        parse: (value: string | null) => {
            // Return the raw value; absent params (null) fall through to validation
            // failure so getTypedParam returns undefined, triggering the explicit
            // sortOptions[0] path in getDefaultSortingOption.
            return value as SortParamValue;
        },
        stringify: (value: SortParamValue) => value.valueOf(),
        validate: (value: SortParamValue) => allSortOptions.includes(value),
    },
    comedian: {
        key: QueryProperty.Comedian,
        defaultValue: "",
        parse: (value: string | null) => {
            return value ?? "";
        },
        stringify: (value: string) => value,
        validate: (value: string) => value.length > 0 || value == "",
    },
    club: {
        key: QueryProperty.Club,
        defaultValue: "",
        parse: (value: string | null) => {
            return value ?? "";
        },
        stringify: (value: string) => value,
        validate: (value: string) => value.length > 0 || value == "",
    },
    zip: {
        key: QueryProperty.Zip,
        defaultValue: "",
        parse: (value: string | null) => {
            return value ?? "";
        },
        stringify: (value: string) => value,
        validate: (value: string) => {
            // Accept 5-digit zip codes, city names (e.g. "Chicago" or "Chicago, IL"),
            // or empty string. Max 60 chars to prevent excessively long inputs.
            return value.length <= 60;
        },
    },
    distance: {
        key: QueryProperty.Distance,
        defaultValue: "",
        parse: (value: string | null) => {
            return value ?? "5";
        },
        stringify: (value: string) => value,
        validate: (value: string) => allDistanceOptions.includes(value),
    },
    toDate: {
        key: QueryProperty.ToDate,
        defaultValue: undefined,
        parse: (value: string | null) => parseToMidnight(value),
        stringify: (value: Date | undefined) => formattedDateParam(value),
        validate: (value: Date | undefined) => isDateTodayOrLater(value),
    },
    fromDate: {
        key: QueryProperty.FromDate,
        defaultValue: undefined,
        parse: (value: string | null) => parseToMidnight(value),
        stringify: (value: Date | undefined) => formattedDateParam(value),
        validate: (value: Date | undefined) => isDateTodayOrLater(value),
    },
    filters: {
        key: QueryProperty.Filters,
        defaultValue: "",
        parse: (value: string | null) => {
            return value ?? "";
        },
        stringify: (value: string) => value,
        validate: (value: string) => value.length > 0 || value == "",
    },
    includeEmpty: {
        key: QueryProperty.IncludeEmpty,
        defaultValue: false,
        parse: (value: string | null) => value === "true",
        stringify: (value: boolean) => (value ? "true" : "false"),
        validate: () => true,
    },
};
