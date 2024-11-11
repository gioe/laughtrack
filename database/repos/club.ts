import { ColumnSet, IDatabase, IMain } from "pg-promise";
import { club as sql } from "../sql";
import {
    PopularityScoreIODTO,
} from "../../objects/interfaces";
import { providedPromiseResponse } from "../../util/promiseUtil";
import { IExtensions } from ".";
import { ClubDTO, PaginatedClubResponseDTO } from "../../objects/classes/club/club.interface";
import { Club } from "../../objects/classes/club/Club";
import { LaughtrackSearchParams } from "../../objects/classes/searchParams/LaughtrackSearchParams";
import { EntityType } from "../../util/enum";
import { PaginatedEntityResponse } from "../../objects/interfaces/entity.interface";

const columnSets: {
    updateScores: ColumnSet | null;
    addAll: ColumnSet | null;
} = {
    updateScores: null,
    addAll: null,
};

export class ClubsRepository {
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
            { table: "clubs" },
        );
        columnSets.addAll = new pgp.helpers.ColumnSet(
            [
                "name",
                "city",
                "zip_code",
                "address",
                "website",
                "scraping_page_url",
                "scraping_config",
                "popularity_score",
            ],
            { table: "clubs" },
        );
    }

    // Creates the table;
    createTable(): Promise<null> {
        return this.db.none(sql.createTable);
    }

    addAll(all: ClubDTO[]): Promise<null> {
        const batchInsert =
            this.pgp.helpers.insert(all, columnSets.addAll) +
            `ON CONFLICT (name) DO UPDATE SET scraping_config = EXCLUDED.scraping_config`;
        return this.db.none(batchInsert);
    }

    // Tries to find a club from id;
    async getByName(name: string, searchParams: LaughtrackSearchParams): Promise<Club | null> {
        return this.db
            .oneOrNone(sql.getByName, {})
            .then((response: ClubDTO | null) =>
                response ? new Club(response) : null,
            );
    }

    async getById(id: number, searchParams: LaughtrackSearchParams): Promise<Club> {
        return this.db
            .oneOrNone(sql.getById, {})
            .then((response: ClubDTO | null) => {
                if (response) {
                    return new Club(response)
                }
                throw new Error(`No club found for id: ${id}`)
            });
    }

    // Returns all club records;
    async getAll(params: LaughtrackSearchParams): Promise<PaginatedEntityResponse> {
        const queryFile = params.getQuery(sql, EntityType.Club)
        const filters = params.asClubQueryFilters();
        return this.db
            .oneOrNone(queryFile, filters)
            .then((result: PaginatedClubResponseDTO | null) => {
                return {
                    entities: result ? result.response.data.map((result: ClubDTO) => new Club(result)) : [],
                    total: result ? result.response.total : 0
                }
            });
    }


    async getAllForScraping(): Promise<Club[]> {
        return this.db
            .any('SELECT * from clubs')
            .then((result: ClubDTO[] | null) => {
                return result ? result.map((result: ClubDTO) => new Club(result)) : []
            });
    }

    updateScores(scores: PopularityScoreIODTO[] | null): Promise<null> {
        if (scores == null) return providedPromiseResponse(null);

        const update =
            this.pgp.helpers.update(scores, columnSets.updateScores) +
            " WHERE v.id = t.id";

        return this.db.none(update);
    }

    async getAllInCity(city: string): Promise<Club[]> {
        return this.db
            .manyOrNone(sql.getByCity, {
                city,
            })
            .then((response: ClubDTO[] | null) =>
                response ? response.map((dto: ClubDTO) => new Club(dto)) : [],
            );
    }


}
