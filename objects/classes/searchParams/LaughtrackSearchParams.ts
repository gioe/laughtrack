

import { URLParam } from "../../../util/enum";
import { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";
import { formatParamValue, getDefaultValueForKey } from "../../../util/primatives/paramUtil";
import { SearchParams } from "../../../app/search/page";

export class LaughtrackSearchParams {
    // Properties
    params: URLSearchParams
    router?: AppRouterInstance;
    path?: string;
    // Constructor
    constructor(params: URLSearchParams, path?: string, router?: AppRouterInstance) {
        this.params = params
        this.router = router
        this.path = path
    }

    static asClientSideParams(params: URLSearchParams, path?: string, router?: AppRouterInstance): LaughtrackSearchParams {
        return new LaughtrackSearchParams(params, path, router);
    }

    static asServerSideParams(params: SearchParams): LaughtrackSearchParams {
        console.log(params)
        console.log(new URLSearchParams(params as Record<string, string>))
        return new LaughtrackSearchParams(new URLSearchParams(params as Record<string, string>));
    }

    setParamValue(key: URLParam, value: string | number | Date) {
        if (value) this.params.set(key, formatParamValue(value));
        else this.params.delete(key);
    }

    getParamValue(key: URLParam): string | number | undefined {
        return this.params.get(key) ?? getDefaultValueForKey(key)
    }

    replaceRoute() {
        this.router?.replace(`${this.path}?${this.params.toString()}`);
    }

    pushPageFromParams() {
        this.router?.push(`/${this.path}?${this.params.toString()}`);
    }

    asShowQueryFilters() {
        return {
            city_id: this.getParamValue(URLParam.City),
            start_date: this.getParamValue(URLParam.StartDate),
            end_date: this.getParamValue(URLParam.EndDate),
            rows: this.getParamValue(URLParam.Rows),
            offset: this.determineOffset()
        }
    }

    determineOffset() {
        const rows = this.getParamValue(URLParam.Rows) as number
        const page = this.getParamValue(URLParam.Page) as number
        return rows * page - 1
    }

}
