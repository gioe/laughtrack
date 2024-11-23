import { ColumnSet, IDatabase, IMain } from 'pg-promise';
import { IExtensions } from '.';
import { ShowDTO } from '../../objects/class/show/show.interface';
import { ComedianDTO } from '../../objects/class/comedian/comedian.interface';
import { LineupItemDTO, ScrapingOutput, TagDTO } from '../../objects/interface';
import { apiActionMap, queryMap } from '../sql';

const columnSets: {
    addAllComedians: ColumnSet | null;
    addAllShows: ColumnSet | null;
    addAllLineupItems: ColumnSet | null;
    addAllShowTags: ColumnSet | null;
} = {
    addAllComedians: null,
    addAllShows: null,
    addAllLineupItems: null,
    addAllShowTags: null
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
        columnSets.addAllShowTags = new pgp.helpers.ColumnSet(['show_id', 'tag_id'], { table: 'tagged_shows' });
    }

    async storeScrapingOutput(data: ScrapingOutput): Promise<null> {
        const showId = await this.storeShow(data.show)

        if (data.comedians.length == 0) {
            return this.queryShowMetadataForComedians(data.show)
                .then((comedians: ComedianDTO[]) => {
                    if (comedians.length === 0) return null
                    return this.addComediansAndLineupItems(comedians, showId)
                })
        }
        return this.addComediansAndLineupItems(data.comedians, showId)
    }

    async storeShow(show: ShowDTO): Promise<number> {
        const id = (await this.addShow(show)).id;
        const tags = await this.db.manyOrNone(queryMap.getTagsFromShowMetadata, {
            showName: show.name.toLocaleLowerCase()
        }) as TagDTO[]
        if (tags.length > 0) {
            console.log(tags)
            const allTags = tags.map((tag: TagDTO) => {
                return {
                    show_id: id,
                    tag_id: tag.id
                }
            })
            const batchInsert = this.pgp.helpers.insert(allTags, columnSets.addAllShowTags) + ' ON CONFLICT DO NOTHING';
            await this.db.any(batchInsert)
        }
        return id
    }

    private async queryShowMetadataForComedians(show: ShowDTO): Promise<ComedianDTO[]> {
        return this.db.manyOrNone(queryMap.getComediansFromShowMetadata, {
            showName: show.name,
            showDescription: show.description
        })
    }

    private async addComediansAndLineupItems(comedians: ComedianDTO[], showId: number): Promise<null> {
        return this.addComedians(comedians)
            .then(() => {
                const lineupItems = comedians.map((comedian: ComedianDTO) => {
                    return {
                        show_id: showId,
                        comedian_id: comedian.uuid ?? ""
                    }
                }) as LineupItemDTO[]
                return this.addLineupItems(lineupItems);
            })
    }

    private addShow(instance: ShowDTO): Promise<{ id: number }> {
        return this.db.one(apiActionMap.addShow, {
            club_id: instance.club_id,
            date: instance.date,
            ticket_link: instance.ticket.link,
            name: instance.name,
            price: instance.ticket.price,
            last_scraped_date: instance.last_scraped_date,
            description: instance.description
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
