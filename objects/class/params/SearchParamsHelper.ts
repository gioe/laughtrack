

import { URLParam } from "../../enum";
import { formatParamValue, getDefaultQueryParamValue } from "../../../util/primatives/paramUtil";
import { URLParams } from "../../type/urlParams";

export class SearchParamsHelper {
    // Properties
    params = new URLSearchParams();
    private static instance: SearchParamsHelper;

    static getInstance() {
        if (!SearchParamsHelper.instance) {
            SearchParamsHelper.instance = new SearchParamsHelper();
        }
        return SearchParamsHelper.instance;
    }

    static async storeParams(urlParams: Promise<URLParams>): Promise<void> {
        return urlParams.then((resolvedParams: URLParams) => {
            this.getInstance().params = new URLSearchParams(resolvedParams as Record<string, string>);
        })
    }

    static setParamValue(key: URLParam, value: string | number | Date) {
        this.getInstance().params.set(key, formatParamValue(value));
    }

    static removeParamValue(key: URLParam,) {
        this.getInstance().params.delete(key);
    }

    static getParamValue(key: URLParam): string | number | undefined {
        return this.getInstance().params.get(key) ?? getDefaultQueryParamValue(key)
    }

    static asParamsString() {
        return this.getInstance().params.toString()
    }


}
