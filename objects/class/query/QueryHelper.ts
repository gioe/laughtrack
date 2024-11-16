import { QueryFileMap } from "../../type/queryFileMap";
import { pageDataMap } from "../../../database/sql";
import pgPromise from "pg-promise";
import { getDB } from "../../../database";
import { ParamsWrapper } from "../params/ParamsWrapper";
import { HeadersWrapper } from "../headers/HeadersWrapper";
import { EntityType } from "../../enum";
const { database } = getDB();

export class QueryHelper {
    // Properties
    queryFileMap: QueryFileMap

    private static getQueryFile(): pgPromise.QueryFile {
        const key = HeadersWrapper.getBasePath()
        const pageQueryMap = pageDataMap[key]
        return pageQueryMap['index']
    }

    private static getCurrentQueryParams(): Record<string, string | number | undefined> {
        const path = HeadersWrapper.getBasePath() as EntityType
        console.log(`We're currently in a ${path} context`)
        switch (path) {
            case EntityType.Club:
                return ParamsWrapper.asClubQueryFilters()
            case EntityType.Show:
                return ParamsWrapper.asShowQueryFilters()
            case EntityType.Comedian:
                return ParamsWrapper.asComedianQueryFilters()
            default:
                return ParamsWrapper.asCommonFilters()
        }
    }

    static async getPageData<T, K>(completionHandler: (response: T) => K): Promise<K> {
        const file = this.getQueryFile()
        const filters = this.getCurrentQueryParams();
        return database.oneOrNone(file, filters).then((value: T | null) => {
            if (value) return completionHandler(value)
            throw new Error(`Failure getting contents of ${file}`)
        })
    }

}
