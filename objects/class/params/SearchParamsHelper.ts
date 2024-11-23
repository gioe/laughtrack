


import { formatParamValue, getDefaultQueryParamValue } from "../../../util/primatives/paramUtil";

enum ParamType {
    Array,
    String
}

interface URLParam {
    type: ParamType
}

type ClientParamValue = string | number | Date;
type ParamsDictValue = string | string[]
type ParamsDict = Map<URLParam, ParamsDictValue>

export class SearchParamsHelper {
    // Properties
    paramsDict: ParamsDict;

    // Our helper will always be initialized with server values, or the values you see in the URL.
    // We will convert this to something more domain specific to align more closely with our
    // business logic.
    constructor(params: URLSearchParams) {
        this.paramsDict = this.initializeParamsDict(params)
    }

    initializeParamsDict(searchParams: URLSearchParams) {
        const newDict = new Map<URLParam, ParamsDictValue>()
        for (const [key, value] of searchParams.entries()) {
            newDict[key] = value
        }
        return newDict;
    }

    updateParamValue(key: URLParam, value: ClientParamValue, isArrayValue = false) {
        const currentKeyValue = this.params.get(key)
        const paramValue = formatParamValue(value) ?? "";
        if (isArrayValue) {
            this.handleArrayParam(key, paramValue, currentKeyValue)
        } else {
            this.setParamValue(key, paramValue);
        }
    }

    handleArrayParam(key: URLParam, newValue: string, currentValue: string | null) {
        let newValues = currentValue?.split(',')
        if (newValues !== undefined) {

            if (newValues.includes(newValue)) {
                newValues = newValues.filter((value: string) => value !== newValue)
            } else {
                newValues.push(newValue)
            }

            if (newValues.length == 0) {
                this.removeParam(key)
            } else {
                this.setParamValue(key, newValues.join(','));
            }

        } else {
            this.setParamValue(key, newValue);
        }
    }

    private setParamValue(key: URLParam, value: string) {
        this.params.set(key, value);
    }

    removeParam(key: URLParam) {
        this.params.delete(key);
    }

    getParamValue(key: URLParam): ParamValue {
        return this.params.get(key) ?? getDefaultQueryParamValue(key)
    }

    asParamsString() {
        return this.params.toString()
    }

    setDefaultValue(key: URLParam, value: ParamValue): void {
        const currentValue = this.getParamValue(key)
        if (currentValue == undefined) {
            const paramValue = formatParamValue(value) ?? "";
            this.setParamValue(key, paramValue)
        }

    }

}
