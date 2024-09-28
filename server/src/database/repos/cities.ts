import {IDatabase, IMain} from 'pg-promise';
import {IResult} from 'pg-promise/typescript/pg-subset.js';
import {ICity} from '../models.js';
import {cities as sql} from '../sql/index.js';

export class CitiesRepository {

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

    // Adds a new city, and returns the new object;
    add(name: string): Promise<ICity> {
        return this.db.one(sql.add, name);
    }

    // Tries to delete a city by id, and returns the number of records deleted;
    remove(id: number): Promise<number> {
        return this.db.result('DELETE FROM cities WHERE id = $1', +id, (r: IResult) => r.rowCount);
    }

    // Tries to find a city from id;
    findById(id: number): Promise<ICity | null> {
        return this.db.oneOrNone('SELECT * FROM cities WHERE id = $1', +id);
    }

    // Tries to find a city from name;
    findByName(name: string): Promise<ICity | null> {
        return this.db.oneOrNone('SELECT * FROM cities WHERE name = $1', name);
    }

    // Returns all city records;
    all(): Promise<ICity[]> {
        return this.db.any('SELECT * FROM cities');
    }

    // Returns the total number of cities;
    total(): Promise<number> {
        return this.db.one('SELECT count(*) FROM cities', [], (a: { count: string }) => +a.count);
    }
}