/* eslint-disable @typescript-eslint/no-explicit-any */

import { SearchParamsHelper } from "../params/SearchParamsHelper";
import { SlugInterface } from "../../interface";
import { QueryProperty } from "../../enum/queryProperty";

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
        const map = new Map<string, any>()

        map.set(QueryProperty.Direction, this.getDirection())
        map.set(QueryProperty.Size, this.getSize())
        map.set(QueryProperty.Page, this.getOffset())
        map.set(QueryProperty.Sort, this.getSortValue())
        map.set(QueryProperty.Params, this.getParams())
        map.set(QueryProperty.Tags, this.getTags())

        const map1 = new Map([...map.entries(), ...this.searchParamsHelper.paramsDict.entries()])
        const obj = Array.from(map1)
            .reduce((obj, [key, value]) => {
                obj[key] = value;
                return obj;
            }, {});

        return obj
    }

    getSortValue() { return this.searchParamsHelper.getParamValue(QueryProperty.Sort) }

    getQueryPattern() {
        const queryValue = this.searchParamsHelper.getParamValue(QueryProperty.Query);
        return { query: `%${queryValue}%` }
    }

    getOffset() {
        const size = Number(this.searchParamsHelper.getParamValue(QueryProperty.Size))
        const page = Number(this.searchParamsHelper.getParamValue(QueryProperty.Page)) - 1
        const offset = size * page
        return (offset == null ? 0 : offset).toString()
    }

    getSize() { return this.searchParamsHelper.getParamValue(QueryProperty.Size) }

    getDirection() { return this.searchParamsHelper.getParamValue(QueryProperty.Direction) }

    getIdentifier() { return decodeURI(this.id ?? "") }

    getParams() { return [''] }

    getTags() { return [''] }

    static async storePageParams(paramsPromise: Promise<any>, slugPromise?: Promise<SlugInterface>) {
        const promises = [paramsPromise, slugPromise]
        return Promise.all(promises).then((values: unknown[]) => {
            const searchParams = new URLSearchParams(values[0] as Record<string, string>)
            const searchParamsHelper = new SearchParamsHelper(searchParams)
            const helper = new QueryHelper(searchParamsHelper, (values[1] as SlugInterface)?.slug)
            return helper.asQueryFilters()
        })
    }

}
