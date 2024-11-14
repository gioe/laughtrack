/* eslint-disable @typescript-eslint/no-explicit-any */
import { ColumnSet, IDatabase, IMain } from "pg-promise";
import { show as sql } from "../sql";
import {
    PopularityScoreIODTO,
    PaginatedEntityCollectionResponse,
    PaginatedEntityCollectionResponseDTO,
    PaginatedEntityResponse,
    PaginatedEntityResponseDTO,
    RepositoryInterface
} from "../../objects/interface";
import { ShowDTO } from "../../objects/class/show/show.interface";
import { IExtensions } from ".";
import { Show } from "../../objects/class/show/Show";

const columnSets: {
    updateScores: ColumnSet | null;
    addAll: ColumnSet | null;
} = {
    updateScores: null,
    addAll: null,
};

export class ShowsRepository implements RepositoryInterface<Show> {
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

    async getAll(filters: any): Promise<PaginatedEntityCollectionResponse<Show>> {
        return this.db
            .oneOrNone(sql.getAll, filters)
            .then((result: PaginatedEntityCollectionResponseDTO<ShowDTO> | null) => {
                return {
                    entities: result ? result.response.data.map((result: ShowDTO) => new Show(result)) : [],
                    total: result ? result.response.total : 0
                }
            });
    }

    async getByProperty(filters: any): Promise<PaginatedEntityResponse<Show>> {
        return this.db
            .oneOrNone(sql.getAll, filters)
            .then((result: PaginatedEntityResponseDTO<ShowDTO> | null) => {
                if (result) {
                    return {
                        entity: new Show(result.response.data),
                        total: result.response.total
                    }
                }
                throw new Error(`No show found`)
            });
    }

    async add(instance: ShowDTO): Promise<{ id: number }> {
        return this.db.one(sql.add, {
            club_id: instance.club_id,
            date: instance.date,
            ticket_link: instance.ticket.link,
            price: instance.ticket.price,
            name: instance.name,
            scraped: instance.scraped
        });
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
