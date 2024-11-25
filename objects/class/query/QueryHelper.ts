/* eslint-disable @typescript-eslint/no-explicit-any */

import { SearchParamsHelper } from "../params/SearchParamsHelper";
import { allQueryProperties, QueryProperty } from "../../enum/queryProperty";
import { formatValue } from "../../../util/primatives/paramUtil";
import { DynamicRoute } from "../../interface/identifable.interface";

// This class is meant to capture all of the page parameters that Next provides us with.
// These are relevant for DB querying and their existence persists across all pages so we capture it
// as globally as possible, updating values according to page transitions.
// It is almost certainly too bloated.
export class QueryHelper {

    identifier?: DynamicRoute
    searchParamsHelper: SearchParamsHelper;

    constructor(searchParamsHelper: SearchParamsHelper, identifier?: DynamicRoute) {
        this.identifier = identifier
        this.searchParamsHelper = searchParamsHelper
    }

    asQueryFilters() {
        return {
            // Sort
            ...this.getSortValue(),
            // Query
            ...this.getQueryPattern(),
            // Page
            ...this.getOffset(),
            // Size
            ...this.getSize(),
            // Direction
            ...this.getDirection(),
            // Identifier
            ...this.getIdentifier(),
            // Params,
            ...this.getParams(),
            // Tags
            ...this.getTags(),
            // Domain Values,
            ...this.getDomainParams()
        }
    }

    getDomainParams() {
        const paramsMap = new Map<string, string>()
        for (const [key, value] of this.searchParamsHelper.paramsDict.entries()) {
            if (!allQueryProperties.includes(key)) {
                paramsMap.set(key, formatValue(value))
            }
        }
        return Object.fromEntries(paramsMap.entries())
    }

    getSortValue() {
        return { sort_by: this.searchParamsHelper.getParamValue(QueryProperty.Sort) }
    }

    getQueryPattern() {
        // const queryValue = this.searchParamsHelper.getParamValue(URLParam.Query);
        return { query: `%${""}%` }
    }

    getOffset() {
        const size = Number(this.searchParamsHelper.getParamValue(QueryProperty.Size))
        const page = Number(this.searchParamsHelper.getParamValue(QueryProperty.Page)) - 1
        const offset = size * page
        return { offset: (offset == null ? 0 : offset) }
    }

    getSize() {
        return { size: this.searchParamsHelper.getParamValue(QueryProperty.Size) ?? 10 }
    }

    getDirection() {
        return { direction: this.searchParamsHelper.getParamValue(QueryProperty.Direction) }
    }

    getIdentifier() {
        if (this.identifier) {
            if (this.identifier.id !== undefined) { return { id: this.identifier.id } }
            if (this.identifier.name !== undefined) { return { name: decodeURI(this.identifier.name) } }
        }
        return {}
    }


    getParams() {
        return { params: [''] }
    }

    getTags() {
        return { tags: [''] }
    }


    static async storePageParams(paramsPromise: Promise<any>, slugPromise?: Promise<QueryHelper>) {
        const promises = [paramsPromise, slugPromise]
        return Promise.all(promises).then((values: unknown[]) => {
            const searchParams = new URLSearchParams(values[0] as string)
            const searchParamsHelper = new SearchParamsHelper(searchParams)
            return new QueryHelper(searchParamsHelper, (values[1] as DynamicRoute))
        })
    }

}
