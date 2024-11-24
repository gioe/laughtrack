import { ClientParamValue } from "../../objects/class/params/SearchParamsHelper";
import { DirectionParamValue, URLParam } from "../../objects/enum";

export const addOrRemoveCommaSeparatedValue = (
    searchParams: URLSearchParams,
    param: string,
    value: string,
): URLSearchParams => {

    const filters = searchParams.get(param);
    let allValues = filters?.split(",") ?? [];
    const valueIncluded = allValues.includes(value);

    if (!valueIncluded) {
        allValues.push(value);
    } else {
        allValues = allValues.filter(
            (paramValues: string) => paramValues !== value,
        );
    }

    if (allValues.length > 0) {
        searchParams.set(param, allValues.join(","));
    } else {
        searchParams.delete(param);
    }

    return searchParams
};

export const formattedDateParam = (value: Date) => {
    const monthDay = value.getDate().toString();
    const month = (value.getMonth() + 1).toString();
    const year = value.getFullYear().toString();
    return `${year}-${month}-${monthDay}`;
};

export const formatParamValue = (value: ClientParamValue) => {
    if (value instanceof Date) {
        return formattedDateParam(value as Date)
    }
    return value.toString()
}


export const getDefaultQueryParamValue = (key: URLParam) => {
    switch (key) {
        case URLParam.Sort:
            return undefined
        case URLParam.Query:
            return ""
        case URLParam.Page:
            return 1
        case URLParam.Size:
            return 10;
        case URLParam.City:
            return ""
        case URLParam.StartDate:
            return undefined
        case URLParam.EndDate:
            return undefined
        case URLParam.Direction:
            return DirectionParamValue.Ascending
        case URLParam.Slug:
            return ""
    }
}
