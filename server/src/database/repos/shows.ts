import {IDatabase, IMain} from 'pg-promise';
import {IResult} from 'pg-promise/typescript/pg-subset.js';
import {IShow} from '../models.js';
import {shows as sql} from '../sql/index.js';
import { ShowInterface } from '../../common/interfaces/show.interface.js';
import { GetFilteredShowsRequest, ShowScore } from '../../api/dto/show.dto.js';

export class ShowsRepository {

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

    // Adds a new show, and returns the new object;
    add(show: ShowInterface): Promise<IShow> {
        return this.db.one(sql.add, name);
    }

    // Tries to delete a show by id, and returns the number of records deleted;
    remove(id: number): Promise<number> {
        return this.db.result('DELETE FROM shows WHERE id = $1', +id, (r: IResult) => r.rowCount);
    }

    // Tries to find a show from id;
    findById(id: number): Promise<IShow | null> {
        return this.db.oneOrNone('SELECT * FROM shows WHERE id = $1', +id);
    }

    // Tries to find a show from name;
    findByName(name: string): Promise<IShow | null> {
        return this.db.oneOrNone('SELECT * FROM shows WHERE name = $1', name);
    }

    // Returns all shows records;
    all(): Promise<IShow[]> {
        return this.db.any('SELECT * FROM shows');
    }

    // Returns the total number of shows;
    total(): Promise<number> {
        return this.db.one('SELECT count(*) FROM shows', [], (a: { count: string }) => +a.count);
    }

    addAll(all: ShowInterface[]): Promise<null> {
        return this.db.none(sql.create);
    }

    getSearchResults(request: GetFilteredShowsRequest): Promise<any[]> {
        return this.db.any(sql.create);
    }

    updateScores(scores: ShowScore[]): Promise<any[]> {
        return this.db.any(sql.create);
    }
}