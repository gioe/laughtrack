import { IDatabase, IMain } from "pg-promise";
import { city as sql } from "../sql";
import { IExtensions } from ".";
import { CityDTO } from "../../objects/classes/city/city.interface";
import { City } from "../../objects/classes/city/City";

export class CityRepository {
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
        private db: IDatabase<IExtensions>,
        private pgp: IMain,
    ) { }

    // Creates the table;
    createTable(): Promise<null> {
        return this.db.none(sql.createTable);
    }
    async getAll(): Promise<City[]> {
        return this.db
            .any(sql.getAll)
            .then((response: CityDTO[] | null) => {
                return response ? response.map((dto: CityDTO) => new City(dto)) : []
            });
    }


}
