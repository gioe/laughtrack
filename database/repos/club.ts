import { ColumnSet, IDatabase, IMain } from "pg-promise";
import { map } from "../sql";
import {
    PaginatedEntityCollectionResponse,
    PaginatedEntityResponse,
    PaginatedEntityResponseDTO,
    PopularityScoreIODTO,
    PaginatedEntityCollectionResponseDTO
} from "../../objects/interface";
import { providedPromiseResponse } from "../../util/promiseUtil";
import { IExtensions } from ".";
import { ClubDTO } from "../../objects/class/club/club.interface";
import { Club } from "../../objects/class/club/Club";
import { QueryHelper } from "../../objects/class/query/QueryHelper";
import { EntityType } from "../../objects/enum";

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

    createTable(): Promise<null> {
        return this.db.none(map.club.createTable);
    }

    async getAll(params: QueryHelper): Promise<PaginatedEntityCollectionResponse> {
        return this.db
            .oneOrNone("", {})
            .then((result: PaginatedEntityCollectionResponseDTO<ClubDTO> | null) => {
                return {
                    entities: result ? result.response.data.map((result: ClubDTO) => new Club(result)) : [],
                    total: result ? result.response.total : 0
                }
            });
    }

    async getByName(name: string, params: QueryHelper): Promise<PaginatedEntityResponse> {
        return this.db
            .oneOrNone("", {})
            .then((result: PaginatedEntityResponseDTO<ClubDTO> | null) => {
                if (result) {
                    return {
                        entity: new Club(result.response.data),
                        total: result.response.total
                    }
                }
                throw new Error(`No club found with name: ${name}`)
            });
    }


    async getById(id: number, params: QueryHelper): Promise<PaginatedEntityResponse> {
        return this.db
            .oneOrNone("", {})
            .then((result: PaginatedEntityResponseDTO<ClubDTO> | null) => {
                if (result) {
                    return {
                        entity: new Club(result.response.data),
                        total: result.response.total
                    }
                }
                throw new Error(`No club found with id: ${name}`)
            });
    }

    async getAllForScraping(): Promise<Club[]> {
        return this.db
            .any('SELECT * from clubs')
            .then((result: ClubDTO[] | null) => {
                return result ? result.map((result: ClubDTO) => new Club(result)) : []
            });
    }

    addAll(all: ClubDTO[]): Promise<null> {
        const batchInsert =
            this.pgp.helpers.insert(all, columnSets.addAll) +
            `ON CONFLICT (name) DO UPDATE SET scraping_config = EXCLUDED.scraping_config`;
        return this.db.none(batchInsert);
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
