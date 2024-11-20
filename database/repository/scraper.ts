import { ColumnSet, IDatabase, IMain } from 'pg-promise';
import { IExtensions } from '.';
import { ShowDTO } from '../../objects/class/show/show.interface';
import { ComedianDTO } from '../../objects/class/comedian/comedian.interface';
import { LineupItemDTO, ScrapingOutput } from '../../objects/interface';
import { apiActionMap } from '../sql';

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
        columnSets.addAllComedians = new pgp.helpers.ColumnSet(['name', 'uuid'], { table: 'comedians' });
        columnSets.addAllLineupItems = new pgp.helpers.ColumnSet(['show_id', 'comedian_id'], { table: 'lineup_items' });
    }

    async storeScrapingOutput(data: ScrapingOutput): Promise<null> {
        const show = await this.addShow(data.show);

        if (data.comedians.length > 0) {
            return this.addComedians(data.comedians)
                .then((comedianIds: { id: number }[]) => {
                    console.log(comedianIds)
                    const lineupItems = data.comedians.map((comedian: ComedianDTO) => {
                        return {
                            show_id: show.id,
                            comedian_id: comedian.uuid ?? ""
                        }
                    }) as LineupItemDTO[]
                    return this.addLineupItems(lineupItems);
                })
        }

        return null
    }

    private addShow(instance: ShowDTO): Promise<{ id: number }> {
        return this.db.one(apiActionMap.addShow, {
            club_id: instance.club_id,
            date: instance.date,
            ticket_link: instance.ticket.link,
            name: instance.name,
            price: instance.ticket.price,
            last_scraped_date: instance.last_scraped_date
        });
    }

    private addComedians(all: ComedianDTO[]): Promise<{ id: number }[]> {
        const batchInsert = this.pgp.helpers.insert(all, columnSets.addAllComedians) + ' ON CONFLICT (uuid) DO NOTHING';
        return this.db.any(batchInsert)
    }

    private addLineupItems(all: LineupItemDTO[]): Promise<null> {
        const batchInsert = this.pgp.helpers.insert(all, columnSets.addAllLineupItems) + ` ON CONFLICT DO NOTHING`;
        return this.db.none(batchInsert)
    }

}
