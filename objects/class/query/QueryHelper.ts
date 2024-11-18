import { QueryFileMap } from "../../type/queryFileMap";
import { pageDataMap } from "../../../database/sql";
import pgPromise from "pg-promise";
import { getDB } from "../../../database";
import { ParamsWrapper } from "../params/ParamsWrapper";
import { HeadersWrapper } from "../headers/HeadersWrapper";
import { EntityType } from "../../enum";
import { SlugWrapper } from "../slug/SlugWrapper";
const { database } = getDB();

export class QueryHelper {
    // Properties
    queryFileMap: QueryFileMap

    private static getQueryFile(): pgPromise.QueryFile {
        const key = HeadersWrapper.getBasePath()
        if (key == 'home') return pageDataMap[key]['index']
        const pageQueryMap = pageDataMap[key]
        const queryType = SlugWrapper.getSlug() ? 'slug' : 'all'
        const queryTypeMap = pageQueryMap[queryType]
        return queryTypeMap['index']
    }

    private static getCurrentQueryParams(): Record<string, string | number | undefined> {

        const path = HeadersWrapper.getBasePath() as EntityType
        const onDetailRoute = SlugWrapper.getSlug() ? true : false

        switch (path) {
            case EntityType.Club:
                return onDetailRoute ? ParamsWrapper.asShowQueryFilters() : ParamsWrapper.asClubQueryFilters()
            case EntityType.Show:
                return ParamsWrapper.asShowQueryFilters()
            case EntityType.Comedian:
                return onDetailRoute ? ParamsWrapper.asShowQueryFilters() : ParamsWrapper.asComedianQueryFilters()
            default:
                return ParamsWrapper.asCommonFilters()
        }
    }

    static async getPageData<T, K>(completionHandler: (response: T) => K): Promise<K> {
        const file = this.getQueryFile()
        const filters = this.getCurrentQueryParams();
        console.log(file)
        console.log(filters)
        return database.one(file, filters).then((value: T) => {
            if (value) return completionHandler(value)
            throw new Error(`Failure getting contents of ${file}`)
        })

    }

}
