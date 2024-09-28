import {IDatabase, IMain} from 'pg-promise';
import {IResult} from 'pg-promise/typescript/pg-subset.js';
import {IComedian} from '../models.js';
import {comedians as sql} from '../sql/index.js';
import { ComedianInterface } from '../../common/interfaces/comedian.interface.js';
import { CreateComedianDTO } from '../../api/dto/comedian.dto.js';

export class ComediansRepository {

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

    // Adds a new comedian, and returns the new object;
    add(comedian: ComedianInterface): Promise<IComedian> {
        return this.db.one(sql.add, comedian);
    }

    // Tries to delete a comedian by id, and returns the number of records deleted;
    remove(id: number): Promise<number> {
        return this.db.result('DELETE FROM comedians WHERE id = $1', +id, (r: IResult) => r.rowCount);
    }

    // Tries to find a comedian from id;
    findById(id: number): Promise<IComedian | null> {
        return this.db.oneOrNone('SELECT * FROM comedians WHERE id = $1', +id);
    }

    // Tries to find a comedian from name;
    findByName(name: string): Promise<IComedian | null> {
        return this.db.oneOrNone('SELECT * FROM comedians WHERE name = $1', name);
    }

    // Returns all comedian records;
    all(): Promise<IComedian[]> {
        return this.db.any('SELECT * FROM comedians');
    }

    // Returns the total number of comedians;
    total(): Promise<number> {
        return this.db.one('SELECT count(*) FROM comedians', [], (a: { count: string }) => +a.count);
    }

    getTrendingComedians(): Promise<IComedian[] | null> {
        return this.db.any(sql.getTrending);
    }

    addAll(all: ComedianInterface[]): Promise<null> {
        return this.db.none(sql.create);
    }
}