/* eslint-disable @typescript-eslint/no-explicit-any */
import { IDatabase, IMain } from 'pg-promise';
import { IExtensions } from '.';
import { queryMap } from '../sql';
import { City } from '../../objects/class/city/City';
import { CityDTO } from '../../objects/interface/city.interface';
import { Club } from '../../objects/class/club/Club';
import { ClubDTO } from '../../objects/class/club/club.interface';

export class QueryRepository {

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
    constructor(private db: IDatabase<IExtensions>, private pgp: IMain) {

    }

    async getClubById(params: any): Promise<any[]> {
        return this.db.any(queryMap.getClubsById, params)
    }

    async getCities(): Promise<City[]> {
        return this.db.manyOrNone(queryMap.getCities).then((cities: CityDTO[] | null) => {
            if (cities) return cities.map((dto: CityDTO) => new City(dto))
            throw new Error("Error getting cities")
        })
    }

    async getClubsInCity(city: {
        name: string;
    }): Promise<Club[]> {
        return this.db.manyOrNone(queryMap.getClubsInCity, city).then((clubs: ClubDTO[] | null) => {
            if (clubs) return clubs.map((dto: ClubDTO) => new Club(dto))
            throw new Error("Error getting clubs")
        })
    }

}
