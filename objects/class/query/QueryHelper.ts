

import { IndexProperty } from "../../enum";
import { QueryFileMap } from "../../type/queryFileMap";
import { Entity, RepositoryInterface } from "../../interface";
import { ParamsWrapper } from "../params/ParamsWrapper";

export interface SQLIndex {
    index: IndexProperty,
    value: string | number;
}

export class QueryHelper {
    // Properties
    paramsWrapper: ParamsWrapper;
    queryFileMap: QueryFileMap

    // Constructor
    constructor(queryFileMap: QueryFileMap, paramsWrapper: ParamsWrapper) {
        this.paramsWrapper = paramsWrapper
        this.queryFileMap = queryFileMap;
    }

    getQueryFile() {
        const fileName = this.paramsWrapper.asMapKey();
        return this.queryFileMap[fileName]
    }

    async getAll<T extends Entity>(repository: RepositoryInterface<T>) {
        const file = this.getQueryFile()
        return repository.getAll(file, this.paramsWrapper.asCommonFilters())
    }

    async getByProperty<T extends Entity>(repository: RepositoryInterface<T>) {
        const file = this.getQueryFile()
        return repository.getByProperty(file, this.paramsWrapper.asCommonFilters())
    }

}
