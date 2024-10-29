import { IDatabase, IMain } from 'pg-promise';
import { IResult } from 'pg-promise/typescript/pg-subset';
import { favorites as sql } from '../sql';
import { CreateFavoriteDTO } from '../../interfaces';

export class FavoritesRepository {

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
        this.createTable();
    }

    // Creates the table;
    createTable(): Promise<null> {
        return this.db.none(sql.create);
    }

    // Adds a new user, and returns the new object;
    add(payload: CreateFavoriteDTO): Promise<boolean> {
        return this.db.one(sql.add, {
            comedian_id: payload.id,
            user_id: payload.user_id
        }, (r: IResult) => true);
    }

    // Tries to delete a user by id, and returns the number of records deleted;
    remove(payload: CreateFavoriteDTO): Promise<boolean> {
        return this.db.result(sql.remove, {
            comedian_id: payload.id,
            user_id: payload.user_id
        }, (r: IResult) => false);
    }

    // Tries to find a user from id;
    findByUserId(id: number): Promise<any | null> {
        return this.db.oneOrNone('SELECT * FROM favorite_comedians WHERE user_id = $1', +id);
    }

}