import { ColumnSet, IDatabase, IMain } from 'pg-promise';
import { IExtensions } from '.';
import { ShowDTO } from '../../objects/class/show/show.interface';
import { ComedianDTO } from '../../objects/class/comedian/comedian.interface';
import { LineupItemDTO } from '../../objects/interface';


const columnSets: {
    addAllComedians: ColumnSet | null;
    addAllShows: ColumnSet | null;
    addAllLineupItems: ColumnSet | null;
} = {
    addAllComedians: null,
    addAllShows: null,
    addAllLineupItems: null
}

export class ScraperRepository {

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
    constructor(private db: IDatabase<IExtensions>, private pgp: IMain) {
        columnSets.addAllShows = new pgp.helpers.ColumnSet(['club_id', 'date_time', 'ticket_link', 'popularity_score'],
            { table: 'shows' });
        columnSets.addAllComedians = new pgp.helpers.ColumnSet(['name', 'uuid_id'], { table: 'comedians' });
        columnSets.addAllLineupItems = new pgp.helpers.ColumnSet(['show_id', 'comedian_id'], { table: 'lineups' });

    }

    addShow(instance: ShowDTO): Promise<{ id: number }> {
        return this.db.one("", {
            club_id: instance.club_id,
            date_time: instance.date,
            ticket_link: instance.ticket.link,
            name: instance.name,
            price: instance.ticket.price
        });
    }

    addComedians(all: ComedianDTO[]): Promise<{ id: number }[]> {
        const batchInsert = this.pgp.helpers.insert(all, columnSets.addAllComedians) + ' ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name, uuid_id = EXCLUDED.uuid_id RETURNING id';
        return this.db.any(batchInsert)
    }

    getComedianIds(uuids: string[]): Promise<{ id: number }[]> {
        return this.db.any("", { uuids })
    }

    addLineupItems(all: LineupItemDTO[]): Promise<null> {
        const batchInsert = this.pgp.helpers.insert(all, columnSets.addAllLineupItems) + ` ON CONFLICT DO NOTHING`;
        return this.db.none(batchInsert)
    }

}
