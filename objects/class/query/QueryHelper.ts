
import { SearchParamsHelper } from "../params/SearchParamsHelper";
import { URLParam } from "../../enum";
import { ReadonlyHeaders } from "next/dist/server/web/spec-extension/adapters/headers";
import { URLParams } from "../../type/urlParams";
import { SlugInterface } from "../../interface";

// This class is meant to capture all of the page parameters that Next provides us with.
// These are relevant for DB querying and their existence persists across all pages so we capture it
// as globally as possible, updating values according to page transitions.
// It is almost certainly too bloated.
export class QueryHelper {

    slug?: string
    headers?: ReadonlyHeaders;
    private static instance: QueryHelper;

    static getInstance() {
        if (!QueryHelper.instance) {
            QueryHelper.instance = new QueryHelper();
        }
        return QueryHelper.instance;
    }

    static asQueryFilters() {
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
        }
    }

    static getSortValue() {
        return { sort: SearchParamsHelper.getParamValue(URLParam.Sort) }
    }

    static getQueryPattern() {
        const queryValue = SearchParamsHelper.getParamValue(URLParam.Query);
        return { query: `%${queryValue ?? ""}%` }
    }

    static getOffset() {
        const size = SearchParamsHelper.getParamValue(URLParam.Size) as number
        const page = (SearchParamsHelper.getParamValue(URLParam.Page) as number) - 1
        return { offset: size * page }
    }

    static getSize() {
        return { size: SearchParamsHelper.getParamValue(URLParam.Size) }
    }

    static getDirection() {
        return { direction: SearchParamsHelper.getParamValue(URLParam.Direction) }
    }

    static getSlug() {
        return QueryHelper.getInstance().slug ? { slug: decodeURI(QueryHelper.getInstance().slug ?? "") } : {}
    }

    static getCityId() {
        return SearchParamsHelper.getParamValue(URLParam.City) ? { city_id: SearchParamsHelper.getParamValue(URLParam.City) } : {}
    }

    static getStartDate() {
        return SearchParamsHelper.getParamValue(URLParam.StartDate) ? { start_date: SearchParamsHelper.getParamValue(URLParam.StartDate) } : {}
    }

    static getEndDate() {
        return SearchParamsHelper.getParamValue(URLParam.EndDate) ? { end_date: SearchParamsHelper.getParamValue(URLParam.EndDate) } : {}
    }

    static async storePageParams(paramsPromise: Promise<URLParams>, headersPromise: Promise<ReadonlyHeaders>,
        slugPromise?: Promise<SlugInterface>) {
        const promises = [SearchParamsHelper.storeParams(paramsPromise), headersPromise, slugPromise]
        return Promise.all(promises).then((values: unknown[]) => {
            QueryHelper.getInstance().headers = values[1] as ReadonlyHeaders
            QueryHelper.getInstance().slug = values[2] ? ((values[2] as SlugInterface).slug) : undefined
        }).then(() => {
            return QueryHelper.asQueryFilters()
        })
    }

}
