/* eslint-disable @typescript-eslint/no-explicit-any */
import pgPromise, { ColumnSet, IDatabase, IMain } from "pg-promise";
import { map } from "../sql";
import {
    PopularityScoreIODTO,
    PaginatedEntityCollectionResponse,
    PaginatedEntityResponse,
    PaginatedEntityResponseDTO,
    RepositoryInterface
} from "../../objects/interface";
import { ShowDTO } from "../../objects/class/show/show.interface";
import { IExtensions } from ".";
import { Show } from "../../objects/class/show/Show";
import { EntityResponse, EntityResponseDTO } from "../../objects/interface/paginatedEntity.interface";

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
    queryUsing: (file: pgPromise.QueryFile, filters: any) => Promise<Show>;
    getAll: (file: pgPromise.QueryFile, filters: any) => Promise<PaginatedEntityCollectionResponse<Show>>;
    getBySlug: (file: pgPromise.QueryFile, filters: any) => Promise<PaginatedEntityResponse<Show>>;

    // Creates the table;
    createTable(): Promise<null> {
        return this.db.none(map.show.ShowCreateTable);
    }

    async getCollection(query: pgPromise.QueryFile, filters: any): Promise<PaginatedEntityResponse<Show>> {
        return this.db
            .oneOrNone(query, filters)
            .then((result: PaginatedEntityResponseDTO<ShowDTO> | null) => {
                return {
                    entities: result ? result.response.data.map((result: ShowDTO) => new Show(result)) : [],
                    total: result ? result.response.total : 0
                }
            });
    }

    async getResource(query: pgPromise.QueryFile, filters: any): Promise<EntityResponse<Show>> {
        return this.db
            .oneOrNone(query, filters)
            .then((result: EntityResponseDTO<ShowDTO> | null) => {
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
        return this.db.one(map.show.ShowAdd, {
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
        return this.db.none(map.show.ShowDeleteClub, {
            clubId: id,
        });
    }
}
