/* eslint-disable @typescript-eslint/no-explicit-any */
import { PaginatedEntityCollectionResponse, PaginatedEntityResponse } from "./paginatedEntity.interface";
import { Entity } from "./entity.interface";
import pgPromise from "pg-promise";

export interface RepositoryInterface<T extends Entity> {
    createTable: () => Promise<null>
    getAll: (file: pgPromise.QueryFile, filters: any) => Promise<PaginatedEntityCollectionResponse<T>>;
    getByProperty: (file: pgPromise.QueryFile, filters: any) => Promise<PaginatedEntityResponse<T>>;

}
