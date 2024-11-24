import { ClientParamValue, ParamsDictValue } from "../../objects/class/params/SearchParamsHelper";

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

export const formatValueFromClient = (value: ClientParamValue) => {
    if (value instanceof Date) {
        return formattedDateParam(value as Date)
    }
    return value.toString()
}

export const formatStoredValues = (value: ParamsDictValue) => {
    if (Array.isArray(value)) {
        return value.join(',')
    }
    return value.toString()
}
