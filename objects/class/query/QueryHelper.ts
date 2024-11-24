/* eslint-disable @typescript-eslint/no-explicit-any */

import { SearchParamsHelper } from "../params/SearchParamsHelper";
import { SlugInterface } from "../../interface";
import { allQueryProperties, QueryProperty } from "../../enum/queryProperty";
import { formatStoredValues } from "../../../util/primatives/paramUtil";

// This class is meant to capture all of the page parameters that Next provides us with.
// These are relevant for DB querying and their existence persists across all pages so we capture it
// as globally as possible, updating values according to page transitions.
// It is almost certainly too bloated.
export class QueryHelper {

    id?: string
    searchParamsHelper: SearchParamsHelper;

    constructor(searchParamsHelper: SearchParamsHelper, id?: string) {
        this.id = id
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
        console.log("GETTING DOMAIN PARAMS")
        const paramsMap = new Map<string, string>()
        console.log(this.searchParamsHelper.paramsDict)
        for (const [key, value] of this.searchParamsHelper.paramsDict.entries()) {
            console.log(`The key is ${key} and the value is ${value}`)
            if (!allQueryProperties.includes(key)) {
                paramsMap.set(key, formatStoredValues(value))
            }
        }
        return paramsMap
    }

    getSortValue() {
        return { sort: this.searchParamsHelper.getParamValue(QueryProperty.Sort) }
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
        return this.id ? { id: decodeURI(this.id ?? "") } : {}
    }


    getParams() {
        return { params: [] }
    }

    getTags() {
        return { tags: [] }
    }


    static async storePageParams(paramsPromise: Promise<any>, slugPromise?: Promise<SlugInterface>) {
        const promises = [paramsPromise, slugPromise]
        return Promise.all(promises).then((values: unknown[]) => {
            console.log(values)
            const searchParams = new URLSearchParams(values[0] as string)
            const searchParamsHelper = new SearchParamsHelper(searchParams)
            const helper = new QueryHelper(searchParamsHelper, (values[1] as SlugInterface)?.slug)
            return helper.asQueryFilters()
        })
    }

}
