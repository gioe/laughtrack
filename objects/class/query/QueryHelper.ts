import { ParamsDictValue, SearchParamsHelper } from "../params/SearchParamsHelper";
import { allQueryProperties, DEFAULT_ERROR, QueryProperty } from "../../enum/queryProperty";
import { DynamicRoute } from "../../interface/identifable.interface";
import { FilterDTO } from "@/objects/interface/filter.interface";

// This class is meant to capture all of the page parameters that Next provides us with.
// These are relevant for DB querying and their existence persists across all pages so we capture it
// as globally as possible, updating values according to page transitions.
// It is almost certainly too bloated.
export class QueryHelper {

    identifier?: DynamicRoute
    searchParamsHelper: SearchParamsHelper;
    filterValues: string[]
    userId?: string | null;

    constructor(searchParamsHelper: SearchParamsHelper,
        filterValues: string[],
        identifier?: DynamicRoute,
        userId?: string | null) {
        this.userId = userId
        this.identifier = identifier
        this.filterValues = filterValues
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
            // Domain Values,
            ...this.getDomainParams(),
            // Filters.
            ...this.getFilters(),
            // UserId
            ...this.getUserId()
        }
    }

    getUserId() {
        return { userId: this.userId }
    }

    getFilters() {

        const filtersEmpty = this.filterValues.length == 0
        return {
            filtersEmpty,
            filters: filtersEmpty ? [''] : this.filterValues
        }
    }

    getDomainParams() {
        const paramsMap = new Map<string, ParamsDictValue>()
        for (const [key, value] of this.searchParamsHelper.paramsDict.entries()) {
            if (!allQueryProperties.includes(key)) {
                paramsMap.set(key, value)
            }
        }
        return Object.fromEntries(paramsMap.entries())
    }

    getSortValue() {
        return { sortBy: this.searchParamsHelper.getParamValue(QueryProperty.Sort) }
    }

    getQueryPattern() {
        const queryValue = this.searchParamsHelper.getParamValue(QueryProperty.Query);
        return { query: `%${queryValue}%` }
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

    static async storePageParams(searchParams: URLSearchParams, filters?: FilterDTO[], identifier?: DynamicRoute, userId?: string | null) {
        const filterValues = filters ? filters.filter((dto) => dto.selected).map((dto: FilterDTO) => dto.display) : [];
        const searchParamsHelper = new SearchParamsHelper(searchParams)
        return new QueryHelper(searchParamsHelper, filterValues, identifier, userId)
    }

}
