import { ParamsDictValue } from "../../objects/class/params/SearchParamsHelper";
import { QueryProperty, SortParamValue } from "../../objects/enum";


export const formattedDateParam = (value: Date) => {
    const monthDay = value.getDate().toString();
    const month = (value.getMonth() + 1).toString();
    const year = value.getFullYear().toString();
    return `${year}-${month}-${monthDay}`;
};

export const formatValue = (value: ParamsDictValue) => {
    if (value instanceof Date) {
        return formattedDateParam(value as Date)
    } else if (Array.isArray(value)) {
        return value.join(',')
    }
    return value.toString()
}

export function setParamDefaults(params: URLSearchParams, path: string): URLSearchParams {

    if (!params.has(QueryProperty.Sort)) { getSortParamDefaultFromPath(params, path) }
    if (!params.has(QueryProperty.Page)) { params.set(QueryProperty.Page, "1") }
    if (!params.has(QueryProperty.Size)) { params.set(QueryProperty.Size, "10") }
    if (!params.has(QueryProperty.Query)) { params.set(QueryProperty.Query, "") }
    if (!params.has(QueryProperty.Direction)) { params.set(QueryProperty.Direction, "asc") }

    return params
}

function getSortParamDefaultFromPath(params: URLSearchParams, path: string): URLSearchParams {
    if (path.startsWith('/club')) {
        if (path.includes('/all')) {
            params.set(QueryProperty.Sort, SortParamValue.Name)
        } else {
            params.set(QueryProperty.Sort, SortParamValue.Date)
        }
    } else if (path.startsWith('/show')) {
        if (path.includes('/all')) {
            params.set(QueryProperty.Sort, SortParamValue.Date)
        } else {
            params.set(QueryProperty.Sort, SortParamValue.Name)
        }
    } else if (path.startsWith('/comedian')) {
        if (path.includes('/all')) {
            params.set(QueryProperty.Sort, SortParamValue.Name)
        } else {
            params.set(QueryProperty.Sort, SortParamValue.Date)
        }
    }
    return params
}
