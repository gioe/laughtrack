import { DirectionParamValue, QueryProperty, SortParamValue } from "@/objects/enum";
import { allDirectionParamValues } from "@/objects/enum/directionParamValue";
import { allDistanceOptions } from "@/objects/enum/distanceValues";
import { allSortOptions } from "@/objects/enum/sortParamValue";
import { SortOptionInterface } from "@/objects/interface";
import { isDateTodayOrLater, parseToMidnight } from "../primatives/dateUtil";

export const getDefaultSortingOption = (sortOptions: SortOptionInterface[],
    sortOption: string | null,
    direction: string | null) => {
    return sortOptions.find(
        (value) =>
            value.value == sortOption &&
            value.direction == direction
    ) ?? sortOptions[0]
}

interface ParamConfig {
    key: string;
    defaultValue: string | number | Date | undefined;
    parse: (value: string | null) => any;
    stringify: (value: any) => string;
    validate: (value: any) => boolean;
}

// Centralized parameter configuration
export const paramConfigs: Record<string, ParamConfig> = {
    page: {
        key: QueryProperty.Page,
        defaultValue: 1,
        parse: (value: string | null) => {
          const parsed = parseInt(value || '1');
          return parsed > 0 ? parsed : 1;
        },
        stringify: (value: number) => value.toString(),
        validate: (value: number) => value > 0
      },
    size: {
        key: QueryProperty.Size,
        defaultValue: 10,
        parse: (value: string| null) => {
            const parsed = parseInt(value || '10');
            return parsed > 0 ? parsed : 10;
        },
        stringify: (value: number) => value.toString(),
        validate: (value: number) => value > 0
    },
    direction: {
        key: QueryProperty.Direction,
        defaultValue: DirectionParamValue.Ascending,
        parse: (value: DirectionParamValue | null): DirectionParamValue => {
            return value || DirectionParamValue.Ascending
        },
        stringify: (value: string) => value,
        validate: (value: string) => {
            return allDirectionParamValues.includes(value);
        }
    },
    sort: {
        key: QueryProperty.Sort,
        defaultValue: SortParamValue.Name,
        parse: (value: SortParamValue | null) => {
            return value ? value : SortParamValue.Name;
        },
        stringify: (value: SortParamValue) => value.valueOf(),
        validate: (value: string) => allSortOptions.includes(value)
    },
    comedian: {
        key: QueryProperty.Comedian,
        defaultValue: "",
        parse: (value: string| null) => {
            return value ?? ""
        },
        stringify: (value: string) => value,
        validate: (value: string) => value.length > 0 || value == ""
    },
    club: {
        key: QueryProperty.Club,
        defaultValue: "",
        parse: (value: string | null) => {
            return value ?? ""
        },
        stringify: (value: string) => value,
        validate: (value: string) => value.length > 0 || value == ""
    },
    zip: {
        key: QueryProperty.Zip,
        defaultValue: "",
        parse: (value: string | null) => {
            return value ?? ""
        },
        stringify: (value: string) => value,
        validate: (value: string) => {
            return value.length > 0 && value.length < 6 || value == ""
        }
    },
    distance: {
        key: QueryProperty.Distance,
        defaultValue: "",
        parse: (value: string | null) => {
            return value ?? '5';
        },
        stringify: (value: string) => value,
        validate: (value: string) => allDistanceOptions.includes(value)
    },
    toDate: {
        key: QueryProperty.ToDate,
        defaultValue: "",
        parse: (value: string| null) =>  parseToMidnight(value),
        stringify: (value: Date | undefined) => value ? value.toISOString().slice(0, 10) : "",
        validate: (value: Date | undefined) => isDateTodayOrLater(value)

    },
    fromDate: {
        key: QueryProperty.FromDate,
        defaultValue: "",
        parse: (value: string| null) => parseToMidnight(value),
        stringify: (value: Date | undefined) => value ? value.toISOString().slice(0, 10) : "",
        validate: (value: Date | undefined) => isDateTodayOrLater(value)
    }
  } as const;
