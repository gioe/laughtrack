import { IDatabase, IMain } from 'pg-promise';
import { search as sql } from '../sql';
import { GetHomeSearchResultsDTO, GetHomeSearchResultsResponseDTO } from '../../interfaces';

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
    constructor(private db: IDatabase<any>, private pgp: IMain) {}

    getHomeSearchResults(request: GetHomeSearchResultsDTO): Promise<GetHomeSearchResultsResponseDTO | null> {
        return this.db.oneOrNone(sql.getHomeSearchResults, {
            location: request.location,
            start_date: request.start_date,
            end_date: request.end_date
        });
    }

}