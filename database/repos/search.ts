import { IDatabase, IMain } from "pg-promise";
import { search as sql } from "../sql";
import {
    GetShowResponseDTO,
    SearchParams,
    ShowInterface,
} from "../../interfaces";
import { toDates } from "../../util/domainModels/show/mapper";

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
    constructor(
        private db: IDatabase<any>,
        private pgp: IMain,
    ) {}

    async getHomeSearchResults(
        request: SearchParams,
    ): Promise<ShowInterface[]> {
        return this.db
            .any(sql.getHomeSearchResults, {
                location: request.location,
                start_date: request.startDate,
                end_date: request.endDate,
            })
            .then((result: GetShowResponseDTO[] | null) =>
                result ? toDates(result) : [],
            );
    }
}
