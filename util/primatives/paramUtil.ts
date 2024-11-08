import { URLParam } from "../enum";

interface URLParamKeyValue {
    key: URLParam,
    value: string | number;
}

export function updateMultipleParams(searchParams: URLSearchParams, values: URLParamKeyValue[]): URLSearchParams {
    values.forEach((val: URLParamKeyValue) => adjustUrlParams(searchParams, val))
    return searchParams
}

export function adjustUrlParams(
    searchParams: URLSearchParams,
    keyValue: URLParamKeyValue,
): URLSearchParams {

    switch (keyValue.key) {
        case URLParam.Sort, URLParam.Query, URLParam.Rows, URLParam.Page:
            return addOrRemoveSingleValue(searchParams, keyValue.key, keyValue.value.toString());
        default:
            return addOrRemoveCommaSeparatedValue(searchParams, keyValue.key, keyValue.value.toString());
    }
}

const addOrRemoveSingleValue = (
    searchParams: URLSearchParams,
    param: string,
    value: string,
): URLSearchParams => {

    if (value) searchParams.set(param, value);
    else searchParams.delete(param);

    return searchParams
};

const addOrRemoveCommaSeparatedValue = (
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
