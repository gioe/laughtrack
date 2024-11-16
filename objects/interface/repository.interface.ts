/* eslint-disable @typescript-eslint/no-explicit-any */
import pgPromise from "pg-promise";

export interface RepositoryInterface<T> {
    createTable: () => Promise<null>
    get: GenericQueryFunction<T>;
}

type GenericQueryFunction<T> = (file: pgPromise.QueryFile, filters: any) => Promise<T>;
