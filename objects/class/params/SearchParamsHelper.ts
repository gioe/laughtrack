


import { URLParam } from "../../enum";
import { formatParamValue, getDefaultQueryParamValue } from "../../../util/primatives/paramUtil";

export type ParamValue = string | number | Date | undefined | null;

export class SearchParamsHelper {
    // Properties
    params: URLSearchParams;
    uuid: string;
    private static instance: SearchParamsHelper;

    constructor(params: URLSearchParams) {
        this.params = params;
        this.uuid = crypto.randomUUID()
    }


    updateParamValue(key: URLParam, value: ParamValue, isArrayValue = false) {
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
