/* eslint-disable @typescript-eslint/no-explicit-any */
import { IDatabase, IMain } from 'pg-promise';
import { IExtensions } from '.';
import { apiActionMap } from '../sql';
import { UserDTO } from '../../objects/interface';
import { ComedianDTO } from '../../objects/class/comedian/comedian.interface';

export class ActionRepository {

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

    async deleteShowsForClub(params: any): Promise<any[]> {
        return this.db.any(apiActionMap.deleteShows, params)
    }

    async addUser(user: UserDTO): Promise<any> {
        return this.db.one(apiActionMap.addUser, {
            email: user.email,
            role: user.role,
            password: user.password
        });
    }

    async addComedian(comedian: ComedianDTO): Promise<any> {
        return this.db.one(apiActionMap.addComedian, {
            name: comedian.name,
            uuid: comedian.uuid,
        });
    }
}
