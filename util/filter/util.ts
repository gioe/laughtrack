import { DirectionParamValue, QueryProperty, SortParamValue } from "@/objects/enum";
import { allDirectionParamValues } from "@/objects/enum/directionParamValue";
import { allDistanceOptions } from "@/objects/enum/distanceValues";
import { allSortOptions } from "@/objects/enum/sortParamValue";
import { SortOptionInterface } from "@/objects/interface";

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
        defaultValue: '5',
        parse: (value: string | null) => {
            return value ?? '5';
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
        stringify: (value: Date | undefined) => value?.toISOString() ?? "",
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
