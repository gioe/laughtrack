import { formatValueFromClient, formatStoredValues } from "../../../util/primatives/paramUtil";
import { QueryProperty } from "../../enum/queryProperty";

type ParamsDict = Map<URLParam, ParamsDictValue>
type ClientParamsDict = Map<URLParam, ClientParamValue>

export type URLParam = QueryProperty | string;
export type ParamsDictValue = string | string[]
export type ClientParamValue = string | number | Date | boolean;

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
            console.log(`The key is ${key} and the value is ${value}`)
            newDict.set(key, value)
        }
        console.log(newDict)
        return newDict;
    }

    updateParamsFromMap(map: ClientParamsDict) {
        for (const [key, value] of map.entries()) {
            this.setParamValue(key, formatValueFromClient(value))
        }
    }

    setParamValue(key: URLParam, value: ClientParamValue) {
        this.paramsDict.set(key, formatValueFromClient(value))
    }

    removeParam(key: URLParam) {
        this.paramsDict.delete(key);
    }

    getParamValue(key: URLParam): string | undefined {
        const paramValue = this.paramsDict.get(key)

        if (paramValue == undefined) { return undefined }
        else if (Array.isArray(paramValue)) { return paramValue.join(',') }
        else return paramValue
    }

    asParamsString() {
        const seachParams = new URLSearchParams()
        for (const [key, value] of this.paramsDict.entries()) {
            seachParams.set(key, formatStoredValues(value))
        }
        return seachParams.toString()
    }

    setDefaultValue(key: URLParam, value: string): void {
        const currentValue = this.getParamValue(key)
        if (currentValue == undefined) {
            this.setParamValue(key, value)
        }

    }

}
