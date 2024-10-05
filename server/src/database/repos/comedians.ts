import { ColumnSet, IDatabase, IMain } from 'pg-promise';
import { IResult } from 'pg-promise/typescript/pg-subset.js';
import { comedians as sql } from '../sql/index.js';
import { CreateComedianDTO } from '../../common/interfaces/data/comedian.interface.js';

var columnSets: {
    updateScores: ColumnSet | null;
    addAll: ColumnSet | null;
} = {
    updateScores: null,
    addAll: null
}

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
        this.create();
        columnSets.updateScores = new pgp.helpers.ColumnSet(['?id', 'popularity_score'], {table: 'comedians'});
        columnSets.addAll = new pgp.helpers.ColumnSet(['name' ], {table: 'comedians'});
    }

    // Creates the table;
    create(): Promise<null> {
        return this.db.none(sql.create);
    }

    // Tries to delete a comedian by id, and returns the number of records deleted;
    remove(id: number): Promise<number> {
        return this.db.result('DELETE FROM comedians WHERE id = $1', +id, (r: IResult) => r.rowCount);
    }

    // Tries to find a comedian from id;
    findById(id: number): Promise<any | null> {
        return this.db.oneOrNone('SELECT * FROM comedians WHERE id = $1', +id);
    }

    // Tries to find a comedian from name;
    findByName(name: string): Promise<any | null> {
        return this.db.oneOrNone(sql.getDetails, {
            name
        });
    }

    // Returns all comedian records;
    all(): Promise<any[]> {
        return this.db.any('SELECT * FROM comedians ORDER BY popularity_score DESC');
    }

    // Returns the total number of comedians;
    total(): Promise<number> {
        return this.db.one('SELECT count(*) FROM comedians', [], (a: { count: string }) => +a.count);
    }

    getTrendingComedians(): Promise<any[] | null> {
        return this.db.any(sql.getTrending);
    }

    addAll(all: CreateComedianDTO[]): Promise<{id: number}[]> {
        const batchInsert = this.pgp.helpers.insert(all, columnSets.addAll) + ' ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id';
        return this.db.any(batchInsert)
    }

    allPopularityData(): Promise<any[] | null> {
        return this.db.any(sql.getAllPopularityData)
    }

    // Tries to delete a comedian by id, and returns the number of records deleted;
    updateScores(scores: any[]): Promise<null> {
        const update = this.pgp.helpers.update(scores, columnSets.updateScores) + ' WHERE v.id = t.id';
        return this.db.none(update)
    }
}