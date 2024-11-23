/* eslint-disable @typescript-eslint/no-explicit-any */

import { SearchParamsHelper } from "../params/SearchParamsHelper";
import { URLParam } from "../../enum";
import { SlugInterface } from "../../interface";

// This class is meant to capture all of the page parameters that Next provides us with.
// These are relevant for DB querying and their existence persists across all pages so we capture it
// as globally as possible, updating values according to page transitions.
// It is almost certainly too bloated.
export class QueryHelper {

    slug?: string
    searchParamsHelper: SearchParamsHelper;
    private static instance: QueryHelper;

    constructor(searchParamsHelper: SearchParamsHelper, slug?: string) {
        this.slug = slug
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
            // Slug
            ...this.getSlug(),
            // City
            ...this.getCityId(),
            // Start Date
            ...this.getStartDate(),
            // End Date
            ...this.getEndDate(),
            // Tags
            ...this.getTags()
        }
    }

    getSortValue() {
        return { sort: this.searchParamsHelper.getParamValue(URLParam.Sort) }
    }

    getQueryPattern() {
        const queryValue = this.searchParamsHelper.getParamValue(URLParam.Query);
        return { query: `%${queryValue ?? ""}%` }
    }

    getOffset() {
        const size = this.searchParamsHelper.getParamValue(URLParam.Size) as number
        const page = (this.searchParamsHelper.getParamValue(URLParam.Page) as number) - 1
        return { offset: size * page }
    }

    getSize() {
        return { size: this.searchParamsHelper.getParamValue(URLParam.Size) }
    }

    getDirection() {
        return { direction: this.searchParamsHelper.getParamValue(URLParam.Direction) }
    }

    getSlug() {
        return this.slug ? { slug: decodeURI(this.slug ?? "") } : {}
    }

    getCityId() {
        return this.searchParamsHelper.getParamValue(URLParam.City) ? { city_id: this.searchParamsHelper.getParamValue(URLParam.City) } : {}
    }

    getStartDate() {
        return this.searchParamsHelper.getParamValue(URLParam.StartDate) ? { start_date: this.searchParamsHelper.getParamValue(URLParam.StartDate) } : {}
    }

    getEndDate() {
        return this.searchParamsHelper.getParamValue(URLParam.EndDate) ? { end_date: this.searchParamsHelper.getParamValue(URLParam.EndDate) } : {}
    }

    getTags() {
        return this.searchParamsHelper.getParamValue(URLParam.EndDate) ? { tags: this.searchParamsHelper.getParamValue(URLParam.EndDate) } : {}
    }

    static async storePageParams(paramsPromise: Promise<any>, slugPromise?: Promise<SlugInterface>) {
        const promises = [paramsPromise, slugPromise]
        return Promise.all(promises).then((values: unknown[]) => {
            const searchParams = new URLSearchParams(values[0] as string)
            const searchParamsHelper = new SearchParamsHelper(searchParams)
            const helper = new QueryHelper(searchParamsHelper, (values[1] as SlugInterface).slug)
            return helper.asQueryFilters()
        })
    }

}
