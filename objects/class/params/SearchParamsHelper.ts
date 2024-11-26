import { ReadonlyURLSearchParams } from "next/navigation";
import { convertValueToString, paramValueIsEmpty } from "../../../util/primatives/paramUtil";
import { QueryProperty, queryPropertyDefaultMap } from "../../enum/queryProperty";

type ParamsDict = Map<URLParam, ParamsDictValue>

export type URLParam = QueryProperty | string;
export type ParamsDictValue = string | string[] | number | Date | boolean;

export class SearchParamsHelper {
    // Properties
    paramsDict: ParamsDict = new Map<URLParam, ParamsDictValue>()

    // Our helper will always be initialized with server values, or the values you see in the URL.
    // We will convert this to something more domain specific to align more closely with our
    // business logic.
    constructor(params: ReadonlyURLSearchParams) {
        for (const [key, value] of params.entries()) {
            this.setParamValue(key, value)
        }
    }

    updateParamsFromMap(map: ParamsDict) {
        for (const [key, value] of map.entries()) {
            this.setParamValue(key, value)
        }
    }

    setParamValue(key: URLParam, value: ParamsDictValue) {
        if (paramValueIsEmpty(value)) {
            this.paramsDict.delete(key)
        } else {
            this.paramsDict.set(key, value)
        }
    }

    removeParam(key: URLParam) {
        this.paramsDict.delete(key);
    }

    getParamValue(key: URLParam): string | string[] {
        const paramValue = this.paramsDict.get(key)
        if (paramValue == undefined) { return queryPropertyDefaultMap.get(key) }
        else if (Array.isArray(paramValue)) { return paramValue }
        else return paramValue.toString()
    }

    asParamsString() {
        const seachParams = new URLSearchParams()
        for (const [key, value] of this.paramsDict.entries()) {
            seachParams.set(key, convertValueToString(value))
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
