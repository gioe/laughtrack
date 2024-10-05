import { ColumnSet, IDatabase, IMain } from 'pg-promise';
import { shows as sql } from '../sql/index.js';
import { CreateShowDTO } from '../../common/interfaces/data/show.interface.js';
import { PopularityScoreDTO } from '../../common/interfaces/data/popularityScore.interface.js';

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
        columnSets.addAll = new pgp.helpers.ColumnSet(['club_id', 'date_time', 'ticket_link', 'popularity_score'],
             { table: 'shows' });
    }

    // Creates the table;
    create(): Promise<null> {
        return this.db.none(sql.create);
    }

    addAll(all: CreateShowDTO[]): Promise<null> {
        return this.db.none(sql.create);
    }

    add(instance: CreateShowDTO): Promise<{id: number}> {
        return this.db.one(sql.add, {
         club_id: instance.club_id,
         date_time: instance.date_time,
         ticket_link: instance.ticket_link  
        });
    }

    // Tries to find a show from id;
    findById(id: number): Promise<any | null> {
        return this.db.oneOrNone(sql.getWithLineup, {
            showId: +id,
        });
    }

    getAllPopularityData(): Promise<any[] | null> {
        return this.db.any(sql.getAllPopularityData)
    }

    updateScores(scores: PopularityScoreDTO[]): Promise<null> {
        const update = this.pgp.helpers.update(scores, columnSets.updateScores) + ' WHERE v.id = t.id';
        return this.db.none(update)
    }
}