

import { EntityType, URLParam } from "../../enum";
import { formatParamValue, getDefaultValueForKey } from "../../../util/primatives/paramUtil";
import { SearchParams } from "../../type/searchParams";
import { getDefaultSortOptionForEntityType } from "../../../util/sort";
import { ReadonlyHeaders } from "next/dist/server/web/spec-extension/adapters/headers";
import { runTasks } from "../../../util/promiseUtil";
import { HeadersWrapper } from "../headers/HeadersWrapper";
import { values } from "lodash";
import { ReadonlyURLSearchParams } from "next/navigation";


export class ParamsWrapper {
    // Properties
    headersWrapper?: HeadersWrapper;
    params: URLSearchParams

    // Constructor
    constructor(params: URLSearchParams, headers?: ReadonlyHeaders) {
        this.params = params
        if (headers) {
            this.headersWrapper = new HeadersWrapper(headers)
        }
    }

    static fromClientSideParams(readOnlyParams: ReadonlyURLSearchParams): ParamsWrapper {
        const mutableParams = new URLSearchParams(readOnlyParams)
        return new ParamsWrapper(mutableParams);
    }

    static async fromServerSideParams(headersPromise: Promise<ReadonlyHeaders>, searchParamsPromise: Promise<SearchParams>): Promise<ParamsWrapper> {
        return runTasks<unknown>([searchParamsPromise, headersPromise])
            .then((vales: unknown[]) => new ParamsWrapper(new URLSearchParams(values[0] as Record<string, string>), vales[1] as ReadonlyHeaders))
    }

    setParamValue(key: URLParam, value: string | number | Date) {
        this.params.set(key, formatParamValue(value));
    }

    removeParamValue(key: URLParam,) {
        this.params.delete(key);
    }

    getParamValue(key: URLParam): string | number | undefined {
        return this.params.get(key) ?? getDefaultValueForKey(key)
    }

    asCommonFilters() {
        return {
            rows: this.getRows(),
            pattern: this.getPattern(),
            offset: this.getOffset()
        }
    }

    asShowPropertyFilters() {
        return {
            city_id: this.getParamValue(URLParam.City),
            start_date: this.getParamValue(URLParam.StartDate),
            end_date: this.getParamValue(URLParam.EndDate),
            ...this.asCommonFilters(),
        }
    }

    asClubQueryFilters() {
        return {
            ...this.asCommonFilters(),
        }
    }

    asComedianQueryFilters() {
        return {
            ...this.asCommonFilters(),
        }
    }

    determineOrderProperties(entityType: EntityType): string {
        const optionalParamvalue = this.getParamValue(URLParam.Sort) as string
        const paramValue = optionalParamvalue == undefined ? getDefaultSortOptionForEntityType(entityType) : optionalParamvalue
        const splitParams = paramValue.split("_")
        return `${splitParams[0]}${splitParams[1]}}`
    }

    getPattern() {
        const queryValue = this.getParamValue(URLParam.Query)
        return `%${queryValue}%`
    }

    getOffset() {
        const rows = this.getParamValue(URLParam.Rows) as number
        const page = this.getParamValue(URLParam.Page) as number
        return rows * page
    }

    getRows() {
        return this.getParamValue(URLParam.Rows)
    }

    asParamsString() {
        return this.params.toString()
    }

    asMapKey() {
        const path = this.headersWrapper?.getPath()
        console.log(path)
        console.log(this.params)
        return `${path}`
    }

}
