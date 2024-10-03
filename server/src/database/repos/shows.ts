import { ColumnSet, IDatabase, IMain } from 'pg-promise';
import { IResult } from 'pg-promise/typescript/pg-subset.js';
import { IShow, IShowPopularityData, IShowPoularityScore } from '../models.js';
import { shows as sql } from '../sql/index.js';
import { ShowInterface, ShowPopularityScore } from '../../common/interfaces/show.interface.js';

var columnSets: {
    updateScores: ColumnSet | null;
    addAll: ColumnSet | null;
} = {
    updateScores: null,
    addAll: null
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
        this.create();
        columnSets.updateScores = new pgp.helpers.ColumnSet(['?id', 'popularity_score'], { table: 'shows' });
        columnSets.addAll = new pgp.helpers.ColumnSet(['club_id', 'date_time', 'ticket_link', 'popularity_score'], { table: 'shows' });
    }

    // Creates the table;
    create(): Promise<null> {
        return this.db.none(sql.create);
    }

    addAll(all: IShow[]): Promise<null> {
        return this.db.none(sql.create);
    }

    // Tries to find a show from id;
    findById(id: number): Promise<IShow | null> {
        return this.db.oneOrNone(sql.getWithLineup, {
            showId: +id,
        });
    }

    getAllPopularityData(): Promise<IShowPopularityData[] | null> {
        return this.db.any(sql.getAllPopularityData)
    }

    updateScores(scores: IShowPoularityScore[]): Promise<null> {
        const update = this.pgp.helpers.update(scores, columnSets.updateScores) + ' WHERE v.id = t.id';
        return this.db.none(update)
    }
}