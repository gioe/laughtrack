import {IDatabase, IMain} from 'pg-promise';
import {IResult} from 'pg-promise/typescript/pg-subset.js';
import {IClub} from '../models.js';
import {clubs as sql} from '../sql/index.js';
import { ClubInterface } from '../../common/interfaces/club.interface.js';

export class ClubsRepository {

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

    addAll(all: ClubInterface[]): Promise<null> {
        return this.db.none(sql.create);
    }

    // Adds a new club, and returns the new object;
    add(payload: ClubInterface): Promise<IClub> {
        return this.db.one(sql.add, name);
    }

    // Tries to delete a club by id, and returns the number of records deleted;
    remove(id: number): Promise<number> {
        return this.db.result('DELETE FROM clubs WHERE id = $1', +id, (r: IResult) => r.rowCount);
    }

    // Tries to find a club from id;
    findById(id: number): Promise<IClub | null> {
        return this.db.oneOrNone(sql.getWithSchedule, {
            clubId: +id,
        });
    }

    // Tries to find a club from name;
    findByName(name: string): Promise<IClub | null> {
        return this.db.oneOrNone('SELECT * FROM clubs WHERE name = $1', name);
    }

    // Tries to find a club from city;
    findByCity(city: string): Promise<IClub[] | null> {
        return this.db.any('SELECT * FROM clubs WHERE city = $1', city);
    }

    getTrendingClubs(): Promise<IClub[] | null> {
        return this.db.any(sql.getTrending);
    }

    // Returns all club records;
    all(): Promise<IClub[]> {
        return this.db.any('SELECT * FROM clubs');
    }

    // Returns the total number of clubs;
    total(): Promise<number> {
        return this.db.one('SELECT count(*) FROM clubs', [], (a: { count: string }) => +a.count);
    }

    delete(id: number): Promise<number> {
        return this.db.result('DELETE FROM clubs WHERE id = $1', +id, (r: IResult) => r.rowCount);
    }

}