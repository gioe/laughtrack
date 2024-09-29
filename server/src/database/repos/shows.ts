import { ColumnSet, IDatabase, IMain } from 'pg-promise';
import { IResult } from 'pg-promise/typescript/pg-subset.js';
import { IShow, IShowPopularityData, IShowSearchResult } from '../models.js';
import { shows as sql } from '../sql/index.js';
import { ShowInterface, ShowPopularityScore } from '../../common/interfaces/show.interface.js';

var columnSets: {
    updateScores: ColumnSet | null;
} = {
    updateScores: null,
}


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
        columnSets.updateScores = new pgp.helpers.ColumnSet(['?id', 'popularity_score'], { table: 'shows' });
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
        return this.db.oneOrNone(sql.getWithLineup, {
            showId: +id,
        });
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

    getSearchResults(request: any): Promise<IShowSearchResult[]> {
        const { location, startDate, endDate } = request
        return this.db.any(sql.getSearchResults, {
            location,
            startDate,
            endDate
        });
    }

    allPopularityData(): Promise<IShowPopularityData[] | null> {
        return this.db.any(sql.allPopularityData)
    }

    updateScores(scores: ShowPopularityScore[]): Promise<null> {
        const update = this.pgp.helpers.update(scores, columnSets.updateScores) + ' WHERE v.id = t.id';
        return this.db.none(update)
    }
}