import { formatParamValue } from "../../../util/primatives/paramUtil";
import { allQueryProperties, QueryProperty } from "../query/queryProperties";

export type ClientParamValue = string | number | Date | boolean;
type URLParam = QueryProperty | string;
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
            // If the key is in the Query Properties list, it means it is a clause to be used on the Postgres Query
            if (allQueryProperties.includes(key)) {
                newDict[key] = value
            }
        }
        console.log(newDict)
        return newDict;
    }

    setParamValue(key: URLParam, value: ClientParamValue) {
        const paramValue = formatParamValue(value);
        this.paramsDict[key] = paramValue
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


    removeParam(key: URLParam) {
        this.paramsDict.delete(key);
    }

    getParamValue(key: URLParam): string | undefined {
        return this.paramsDict.get(key)
    }

    asParamsString() {
        return this.paramsDict.toString()
    }

    setDefaultValue(key: URLParam, value: string): void {
        const currentValue = this.getParamValue(key)
        if (currentValue == undefined) {
            const paramValue = formatParamValue(value) ?? "";
            this.setParamValue(key, paramValue)
        }

    }

}
