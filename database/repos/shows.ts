import { ColumnSet, IDatabase, IMain } from 'pg-promise';
import { shows as sql } from '../sql';
import { PopularityScoreIODTO, GroupedPopularityScoreDTO, CreateShowDTO, GetShowResponseDTO  } from '../../interfaces';

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
        columnSets.updateScores = new pgp.helpers.ColumnSet(['?id', 'popularity_score'], { table: 'shows' });
        columnSets.addAll = new pgp.helpers.ColumnSet(['club_id', 'date_time', 'ticket_link', 'popularity_score'],
            { table: 'shows' });
    }

    // Creates the table;
    createTable(): Promise<null> {
        return this.db.none(sql.create);
    }

    add(instance: CreateShowDTO): Promise<{ id: number }> {
        return this.db.one(sql.add, {
            club_id: instance.club_id,
            date_time: instance.date_time,
            ticket_link: instance.ticket_link,
            name: instance.name,
            price: instance.price
        });
    }

    // Tries to find a show from id;
    findById(id: number): Promise<GetShowResponseDTO | null> {
        return this.db.oneOrNone(sql.getWithLineup, {
            showId: +id,
        });
    }

    getAllLineupPopularityData(): Promise<GroupedPopularityScoreDTO[] | null> {
        return this.db.any(sql.getAllLineupPopularityData)
    }

    updateScores(scores: PopularityScoreIODTO[]): Promise<null> {
        const update = this.pgp.helpers.update(scores, columnSets.updateScores) + ' WHERE v.id = t.id';
        return this.db.none(update)
    }

    deleteForClub(id: number): Promise<null> {
        return this.db.none(sql.deleteByClub, {
            clubId: id
        })
    }

}