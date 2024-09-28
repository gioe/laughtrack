import {IDatabase, IMain} from 'pg-promise';
import {IResult} from 'pg-promise/typescript/pg-subset.js';
import {IShowComedian} from '../models.js';
import {showComedians as sql} from '../sql/index.js';

export class ShowComediansRepository {

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
        /*
          If your repository needs to use helpers like ColumnSet,
          you should create it conditionally, inside the constructor,
          i.e. only once, as a singleton.
        */
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
    add(name: string): Promise<IShowComedian> {
        return this.db.one(sql.add, name);
    }

    // Tries to delete a user by id, and returns the number of records deleted;
    remove(id: number): Promise<number> {
        return this.db.result('DELETE FROM show_comedians WHERE id = $1', +id, (r: IResult) => r.rowCount);
    }

    // Tries to find a user from id;
    findById(id: number): Promise<IShowComedian | null> {
        return this.db.oneOrNone('SELECT * FROM show_comedians WHERE id = $1', +id);
    }

    // Tries to find a user from name;
    findByName(name: string): Promise<IShowComedian | null> {
        return this.db.oneOrNone('SELECT * FROM show_comedians WHERE name = $1', name);
    }

    // Returns all user records;
    all(): Promise<IShowComedian[]> {
        return this.db.any('SELECT * FROM show_comedians');
    }

    // Returns the total number of users;
    total(): Promise<number> {
        return this.db.one('SELECT count(*) FROM show_comedians', [], (a: { count: string }) => +a.count);
    }
}