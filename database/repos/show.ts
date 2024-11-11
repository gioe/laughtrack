import { ColumnSet, IDatabase, IMain } from "pg-promise";
import { show as sql } from "../sql";
import {
    PopularityScoreIODTO,
} from "../../objects/interfaces";
import { ShowDTO } from "../../objects/classes/show/show.interface";
import { IExtensions } from ".";
import { Show } from "../../objects/classes/show/Show";
import { LaughtrackSearchParams } from "../../objects/classes/searchParams/LaughtrackSearchParams";

const columnSets: {
    updateScores: ColumnSet | null;
    addAll: ColumnSet | null;
} = {
    updateScores: null,
    addAll: null,
};

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
    constructor(
        private db: IDatabase<IExtensions>,
        private pgp: IMain,
    ) {
        columnSets.updateScores = new pgp.helpers.ColumnSet(
            ["?id", "popularity_score"],
            { table: "shows" },
        );
        columnSets.addAll = new pgp.helpers.ColumnSet(
            ["club_id", "date_time", "ticket_link", "popularity_score"],
            { table: "shows" },
        );
    }

    // Creates the table;
    createTable(): Promise<null> {
        return this.db.none(sql.createTable);
    }

    async getAll(params: LaughtrackSearchParams): Promise<Show[]> {
        return this.db
            .any(sql.getAll, params.asShowQueryFilters())
            .then((results: ShowDTO[] | null) => {
                return results ? results.map((result: ShowDTO) => new Show(result)) : []
            });
    }

    async add(instance: ShowDTO): Promise<{ id: number }> {
        return this.db.one(sql.add, {
            club_id: instance.club_id,
            date_time: instance.date_time,
            ticket_link: instance.ticket.link,
            price: instance.ticket.price,
            name: instance.name,
            last_scrape_time: instance.last_scrape_time
        });
    }

    // Tries to find a show from id;
    async getById(id: number): Promise<Show | null> {
        return this.db
            .oneOrNone(sql.getById, {
                showId: +id,
            })
            .then((show: ShowDTO | null) =>
                show ? new Show(show) : null,
            );
    }

    async updateScores(scores: PopularityScoreIODTO[]): Promise<null> {
        const update =
            this.pgp.helpers.update(scores, columnSets.updateScores) +
            " WHERE v.id = t.id";
        return this.db.none(update);
    }

    async deleteForClub(id: number): Promise<null> {
        return this.db.none(sql.deleteByClub, {
            clubId: id,
        });
    }
}
