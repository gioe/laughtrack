import { DirectionParamValue, QueryProperty, SortParamValue } from "@/objects/enum";
import { allDirectionParamValues } from "@/objects/enum/directionParamValue";
import { allDistanceOptions } from "@/objects/enum/distanceValues";
import { allSortOptions } from "@/objects/enum/sortParamValue";
import { SortOptionInterface } from "@/objects/interface";

export const getDefaultSortingOption = (sortOptions: SortOptionInterface[], sortOption: string | null, direction: string | null) => {
    return sortOptions.find(
        (value) =>
            value.value == sortOption &&
            value.direction == direction
    ) ?? sortOptions[0]
}

// config/urlParams.ts
export interface ParamConfig<T> {
    key: string;
    defaultValue: T;
    parse: (value: string | null) => T;
    stringify: (value: T) => string;
    validate?: (value: T) => boolean;
    _type?: T; // Type helper - never used at runtime
}

// Centralized parameter configuration
export const paramConfigs = {
    page: {
        key: QueryProperty.Page,
        defaultValue: 1,
        parse: (value: string | null) => {
          const parsed = parseInt(value || '1', 10);
          return parsed > 0 ? parsed : 1;
        },
        stringify: (value: number) => value.toString(),
        validate: (value: number) => value > 0
      },
    size: {
        key: QueryProperty.Size,
        defaultValue: 10,
        parse: (value: string| null) => {
            const parsed = parseInt(value || '10', 10);
            return parsed > 0 ? parsed : 10;
        },
        stringify: (value: number) => value.toString(),
        validate: (value: number) => value > 0
    },
    direction: {
        key: QueryProperty.Direction,
        defaultValue: DirectionParamValue.Ascending,
        parse: (value: string| null) => {
            return value ? value : DirectionParamValue.Ascending;
        },
        stringify: (value: DirectionParamValue) => value.valueOf(),
        validate: (value: string) => allDirectionParamValues.includes(value)
    },
    sort: {
        key: QueryProperty.Sort,
        defaultValue: SortParamValue.Name,
        parse: (value: string | null) => {
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
        validate: (value: string) => value !== ""
    },
    club: {
        key: QueryProperty.Club,
        defaultValue: "",
        parse: (value: string | null) => {
            return value ?? ""
        },
        stringify: (value: string) => value,
        validate: (value: string) => value !== ""
    },
    zip: {
        key: QueryProperty.Zip,
        defaultValue: '10003',
        parse: (value: string | null) => {
            return value ?? "10003"
        },
        stringify: (value: string) => value,
        validate: (value: string) => {
            const cleanZip = value.trim();
            const zipRegex = /^[0-9]{5}(?:-[0-9]{4})?$/;
            return zipRegex.test(cleanZip);
        }
    },
    distance: {
        key: QueryProperty.Distance,
        defaultValue:  "5",
        parse: (value: string | null) => {
            return value ?? "5"
        },
        stringify: (value: string) => value,
        validate: (value: string) => allDistanceOptions.includes(value)
    },
    toDate: {
        key: QueryProperty.ToDate,
        defaultValue: undefined,
        parse: (value: string| null) => {
            const to = new Date(value ?? "");
            return isNaN(to.getTime()) ? undefined : to
        },
        stringify: (value: Date | undefined) => value?.toISOString(),
        validate: (value: Date | undefined) => {
            return value == undefined || value > new Date()
        }
    },
    fromDate: {
        key: QueryProperty.FromDate,
        defaultValue: new Date(),
        parse: (value: string | null) => {
            const from = new Date(value ?? "");
            return isNaN(from.getTime()) ? new Date() : from
        },
        stringify: (value: Date) => value.toISOString(),
        validate: (value: Date) => {
            return value >= new Date()
        }
    }
  } as const;
