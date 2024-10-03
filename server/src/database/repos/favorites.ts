import {IDatabase, IMain} from 'pg-promise';
import {IResult} from 'pg-promise/typescript/pg-subset.js';
import {favorites as sql} from '../sql/index.js';

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
        this.create();
    }

    // Creates the table;
    create(): Promise<null> {
        return this.db.none(sql.create);
    }

    // Drops the table;
    drop(): Promise<null> {
        return this.db.none(sql.drop);
    }

    // Removes all records from the table;
    empty(): Promise<null> {
        return this.db.none(sql.empty);
    }

    // Adds a new user, and returns the new object;
    add(comedianId: number, userId: number): Promise<any> {
        return this.db.one(sql.add, {
            comedianId, userId
        });
    }

    // Tries to delete a user by id, and returns the number of records deleted;
    remove(comedianId: number, userId: number): Promise<number> {
        return this.db.result('DELETE FROM favorites WHERE comedian_id = $1 AND user_id = $2', {
            comedianId, userId
        }, (r: IResult) => r.rowCount);
    }

    // Tries to find a user from id;
    findByUserId(id: number): Promise<any | null> {
        return this.db.oneOrNone('SELECT * FROM favorites WHERE user_id = $1', +id);
    }

}