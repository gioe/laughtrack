import { ParamsDictValue } from "../../objects/class/params/SearchParamsHelper";

export const paramValueIsEmpty = (value: ParamsDictValue) => {
    if (Array.isArray(value)) { return value.length == 0 }
    else return value == '' || value == undefined
}

export const formattedDateParam = (value: Date) => {
    const monthDay = value.getDate().toString();
    const month = (value.getMonth() + 1).toString();
    const year = value.getFullYear().toString();
    return `${year}-${month}-${monthDay}`;
};

export const convertValueToString = (value: ParamsDictValue) => {
    if (value instanceof Date) {
        return formattedDateParam(value as Date)
    } else if (Array.isArray(value)) {
        return value.join(',')
    }
    return value.toString()
}
