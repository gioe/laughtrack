import {ColumnSet, IDatabase, IMain} from 'pg-promise';
import {IResult} from 'pg-promise/typescript/pg-subset.js';
import {lineups as sql} from '../sql/index';
import { CreateLineupItemDTO, GetLineupItemDTO, UpdateLineupItemDTO} from '../../interfaces';

var columnSets: {
    addAll: ColumnSet | null;
    updateItems: ColumnSet | null;
} = {
    addAll: null, 
    updateItems: null
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
        this.createTable();
        columnSets.addAll = new pgp.helpers.ColumnSet(['show_id', 'comedian_id' ], {table: 'lineups'});
        columnSets.updateItems = new pgp.helpers.ColumnSet(['?id', 'comedian_id' ], {table: 'lineups'});
    }

    // Creates the table;
    createTable(): Promise<null> {
        return this.db.none(sql.create);
    }

    addAll(all: CreateLineupItemDTO[]): Promise<null> {
        const batchInsert = this.pgp.helpers.insert(all, columnSets.addAll) + ` ON CONFLICT DO NOTHING`;
        return this.db.none(batchInsert)
    }

    // Tries to delete a user by id, and returns the number of records deleted;
    remove(comedianId: number, showId: number): Promise<number> {
        return this.db.result('DELETE FROM lineups WHERE comedian_id = $1 AND show_id = $2', {
            comedianId, showId
        }, (r: IResult) => r.rowCount);
    }

    // Tries to find a user from id;
    findByShowId(showId: number): Promise<any | null> {
        return this.db.oneOrNone(sql.getByShowId, {
            showId
        });
    }

    // Tries to find a user from name;
    findByComedianId(comedianId: number): Promise<GetLineupItemDTO[] | null> {
        return this.db.any(sql.getByComedianId, {
            comedianId
        });
        
    }

    updateLineups(updateRecords: UpdateLineupItemDTO[]): Promise<any[]> {
        const update = this.pgp.helpers.update(updateRecords, columnSets.updateItems) + ' WHERE v.id = t.id RETURNING 1';
        return this.db.manyOrNone(update)
    }


}