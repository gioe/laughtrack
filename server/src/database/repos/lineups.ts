import {IDatabase, IMain} from 'pg-promise';
import {IResult} from 'pg-promise/typescript/pg-subset.js';
import {IUser} from '../models.js';
import {lineups as sql} from '../sql/index.js';
import { UserInterface } from '../../common/interfaces/user.interface.js';

export class LineupsRepository {

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
    add(comedianId: number, showId: number): Promise<IUser> {
        return this.db.one(sql.add, {
            comedianId, showId
        });
    }

    // Tries to delete a user by id, and returns the number of records deleted;
    remove(comedianId: number, showId: number): Promise<number> {
        return this.db.result('DELETE FROM lineups WHERE comedian_id = $1 AND show_id = $2', {
            comedianId, showId
        }, (r: IResult) => r.rowCount);
    }

    // Tries to find a user from id;
    findByShowId(showId: number): Promise<IUser | null> {
        return this.db.oneOrNone('SELECT * FROM lineups WHERE show_id = $1', {
            showId
        });
    }

    // Tries to find a user from name;
    findByComedianId(comedianId: number): Promise<IUser | null> {
        return this.db.oneOrNone('SELECT * FROM lineups WHERE comedian_id = $1', {
            comedianId
        });
    }

}