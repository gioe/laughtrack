

import { EntityType, URLParam } from "../../../util/enum";
import { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";
import { formatParamValue, getDefaultValueForKey } from "../../../util/primatives/paramUtil";
import { SearchParams } from "../../types/searchParams";
import { getDefaultSortOptionForEntityType } from "../../../util/sort";
import { QueryFileMap } from "../../types/queryFileMap";

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

    pushPageFromParams(providedPath: string) {
        this.router?.push(`/${providedPath}?${this.params.toString()}`);
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

    asClubQueryFilters() {
        return {
            rows: this.getParamValue(URLParam.Rows),
            offset: this.determineOffset(),
            query: this.determineQuery()
        }
    }

    asComedianQueryFilters() {
        return {
            rows: this.getParamValue(URLParam.Rows),
            offset: this.determineOffset(),
            query: this.determineQuery()
        }
    }

    determineOffset() {
        const rows = this.getParamValue(URLParam.Rows) as number
        const page = this.getParamValue(URLParam.Page) as number
        return rows * page
    }

    determineOrderProperites(entityType: EntityType): { property: string, direction: string } {
        const optionalParamvalue = this.getParamValue(URLParam.Sort) as string
        const paramValue = optionalParamvalue == undefined ? getDefaultSortOptionForEntityType(entityType) : optionalParamvalue
        const splitParams = paramValue.split("_")
        return {
            property: splitParams[0],
            direction: splitParams[1]
        }
    }

    getQuery(map: QueryFileMap, entityType: EntityType) {
        const sortParamValues = this.determineOrderProperites(entityType)
        const fileKey = `getAllBy${sortParamValues.property}${sortParamValues.direction}`
        return map[fileKey]
    }

    determineQuery() {
        const queryValue = this.getParamValue(URLParam.Query)
        return `%${queryValue}%`
    }

}
