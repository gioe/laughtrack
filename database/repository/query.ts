/* eslint-disable @typescript-eslint/no-explicit-any */
import { IDatabase, IMain } from 'pg-promise';
import { IExtensions } from '.';
import { queryMap } from '../sql';
import { Club } from '../../objects/class/club/Club';
import { ClubDTO } from '../../objects/class/club/club.interface';
import { EntityType } from '../../objects/enum';
import { CityDTO } from '../../objects/class/city/city.interface';
import { TagDataDTO } from '../../objects/interface/tag.interface';

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
    constructor(private db: IDatabase<IExtensions>, private pgp: IMain) { }

    async getAllClubs(): Promise<ClubDTO[]> {
        return this.db.manyOrNone(queryMap.getAllClubs)
            .then((clubs: ClubDTO[] | null) => {
                if (clubs) return clubs
                throw new Error("Error getting clubs")
            })
    }

    async getClubById(params: any): Promise<any[]> {
        return this.db.any(queryMap.getClubById, params)
    }

    async getClubsByIds(ids: string[]): Promise<any[]> {
        return this.db.any(queryMap.getClubsByIds, [ids])
    }

    async getShowById(id: number): Promise<any> {
        return this.db.oneOrNone(queryMap.getShowById, {
            id
        });
    }

    async getCities(): Promise<CityDTO[]> {
        return this.db.manyOrNone(queryMap.getCities)
    }

    async getClubsInCity(city: {
        name: string;
    }): Promise<Club[]> {
        return this.db.manyOrNone(queryMap.getClubsInCity, city).then((clubs: ClubDTO[] | null) => {
            if (clubs) return clubs.map((dto: ClubDTO) => new Club(dto))
            throw new Error("Error getting clubs")
        })
    }

    async userExists(email: string): Promise<any | null> {
        return this.db.oneOrNone('SELECT * FROM users WHERE email = $1', email);
    }

    async getTags(entityType: EntityType): Promise<TagDataDTO[]> {
        return this.db.manyOrNone(queryMap.getTagsByType, {
            type: entityType.valueOf()
        })
    }

}
