


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

    setParamValue(key: URLParam, value: ParamValue) {
        this.params.set(key, formatParamValue(value) ?? "");
    }

    removeParamValue(key: URLParam) {
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
