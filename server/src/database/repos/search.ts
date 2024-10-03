import { IDatabase, IMain } from 'pg-promise';
import { search as sql } from '../sql/index.js';

export class SearchRepository {

    /**
     * @param db
     * Automated database connection context/interface.
     *
     * If you ever need to access other repositories from this one,
     * you will have to replace type 'IDatabase<any>' with 'any'.
     *
     * @param pgp
     * Library's root, if ever needed, like to access 'helpers'
     * or other namespaces available from the root.
     */
    constructor(private db: IDatabase<any>, private pgp: IMain) {

    }

    getHomeSearchResults(request: any): Promise<any | null> {
        const { location, startDate, endDate } = request
        return this.db.oneOrNone(sql.getHomeSearchResults, {
            location,
            startDate,
            endDate
        });
    }

}