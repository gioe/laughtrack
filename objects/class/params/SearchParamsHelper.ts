


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

    addOrRemoveParamValue(key: URLParam, value: ParamValue) {
        if (this.params.getAll(key).includes(value as string)) {
            this.params.delete(key)
        }
        this.params.append(key, formatParamValue(value) ?? "");
        console.log(this.params.getAll(key))
    }

    setParamValue(key: URLParam, value: ParamValue, isArrayValue = false) {
        const values = this.params.getAll(key)
        const paramValue = formatParamValue(value) ?? "";

        if (isArrayValue) {
            if (values.includes(paramValue)) {
                const newValues = values.filter((value: string) => value !== paramValue)
                if (newValues.length == 0) {
                    this.removeParam(key)
                } else {
                    this.params.set(key, newValues.join(','));
                }
            } else {
                const newValues = [...values, paramValue]
                this.params.set(key, newValues.join(','));
            }
        } else {
            this.params.set(key, paramValue);
        }

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
            this.setParamValue(key, value)
        }

    }

}
