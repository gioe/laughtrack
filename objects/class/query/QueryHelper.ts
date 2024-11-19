import { QueryFileMap } from "../../type/queryFileMap";
import { pageDataMap } from "../../../database/sql";
import pgPromise from "pg-promise";
import { SearchParamsHelper } from "../params/SearchParamsHelper";
import { HeaderKey, RestApiAction, URLParam } from "../../enum";
import { ReadonlyHeaders } from "next/dist/server/web/spec-extension/adapters/headers";
import { URLParams } from "../../type/urlParams";
import { getDB } from "../../../database";
import { SlugInterface } from "../../interface";
import { getDefaultHeaderValue } from "../../../util/primatives/headerUtil";
const { database } = getDB();

const indexKey = 'index';

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

    static async storePageParams(paramsPromise: Promise<URLParams>, headersPromise: Promise<ReadonlyHeaders>, slugPromise?: Promise<SlugInterface>) {
        const promises = [SearchParamsHelper.storeParams(paramsPromise), headersPromise, slugPromise]
        return Promise.all(promises).then((values: unknown[]) => {
            QueryHelper.getInstance().headers = values[1] as ReadonlyHeaders
            QueryHelper.getInstance().slug = values[2] ? ((values[2] as SlugInterface).slug) : undefined
        })
    }

    static async storeSearchParams(params: Promise<URLParams>) {
        await SearchParamsHelper.storeParams(params);
    }

    private static getEntityMap() {
        const key = QueryHelper.getBasePath()
        return pageDataMap[key]
    }

    private static getEntityCollectionMap(map: QueryFileMap) {
        const key = QueryHelper.getInstance().slug ? 'slug' : 'all'
        return map[key]
    }

    private static getPageDataQueryFile(): pgPromise.QueryFile {
        const entityMap = QueryHelper.getEntityMap()
        const collectionMap = QueryHelper.getEntityCollectionMap(entityMap);
        return collectionMap ? collectionMap[indexKey] : entityMap[indexKey]
    }

    // We're keeping track of the current url path in the request headers.
    // The "base" path is always the element at index 1 and we use this as our query map key.
    static getBasePath() {
        const fullPath = QueryHelper.getValue(HeaderKey.Path)
        const pathElements = fullPath.split('/')
        const basePath = pathElements[1];

        // We can't work with an empty string, so for the landing page, we'll hijack and call it home for now.
        if (basePath == '') return 'home'
        else return basePath
    }

    static getValue(key: HeaderKey) {
        return QueryHelper.getInstance().headers?.get(key.valueOf()) ?? getDefaultHeaderValue(key)
    }

    private static getApiActionFile(action: RestApiAction): pgPromise.QueryFile {
        const entityMap = QueryHelper.getEntityMap()
        const collectionMap = QueryHelper.getEntityCollectionMap(entityMap);
        const actionMap = collectionMap[action.valueOf()]
        return actionMap[indexKey]
    }

    static async getPageData<T, K>(completionHandler: (response: T) => K): Promise<K> {
        const file = this.getPageDataQueryFile()
        const filters = this.asQueryFilters();

        return database.one(file, filters).then((value: T) => {
            if (value) return completionHandler(value)
            throw new Error(`Failure getting contents of ${file}`)
        })
    }


}
