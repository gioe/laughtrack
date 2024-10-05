import {ColumnSet, IDatabase, IMain} from 'pg-promise';
import {IResult} from 'pg-promise/typescript/pg-subset.js';
import {lineups as sql} from '../sql/index.js';
import { CreateLineupItemDTO } from '../../common/interfaces/data/lineupItem.interface.js';

var columnSets: {
    addAll: ColumnSet | null;
} = {
    addAll: null
}


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
        columnSets.addAll = new pgp.helpers.ColumnSet(['show_id', 'comedian_id' ], {table: 'lineups'});
    }

    // Creates the table;
    create(): Promise<null> {
        return this.db.none(sql.create);
    }

    addAll(all: CreateLineupItemDTO[]): Promise<null> {
        const batchInsert = this.pgp.helpers.insert(all, columnSets.addAll) + ` ON CONFLICT DO NOTHING`;
        return this.db.none(batchInsert)
    }

    // Adds a new user, and returns the new object;
    add(lineupItem: CreateLineupItemDTO): Promise<any> {
        return this.db.one(sql.add, {
            show_id: lineupItem.show_id,
            comedian_id: lineupItem.comedian_id,
        });
    }

    // Tries to delete a user by id, and returns the number of records deleted;
    remove(comedianId: number, showId: number): Promise<number> {
        return this.db.result('DELETE FROM lineups WHERE comedian_id = $1 AND show_id = $2', {
            comedianId, showId
        }, (r: IResult) => r.rowCount);
    }

    // Tries to find a user from id;
    findByShowId(showId: number): Promise<any | null> {
        return this.db.oneOrNone('SELECT * FROM lineups WHERE show_id = $1', {
            showId
        });
    }

    // Tries to find a user from name;
    findByComedianId(comedianId: number): Promise<any | null> {
        return this.db.oneOrNone('SELECT * FROM lineups WHERE comedian_id = $1', {
            comedianId
        });
    }

}