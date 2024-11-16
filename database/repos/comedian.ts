import { ColumnSet, IDatabase, IMain } from "pg-promise";
import { map } from "../sql";
import { providedPromiseResponse } from "../../util/promiseUtil";
import { ComedianDTO } from "../../objects/class/comedian/comedian.interface";
import {
    PaginatedEntityResponse,
    PaginatedEntityCollectionResponseDTO,
    PopularityScoreIODTO,
    SocialDataDTO,
    PaginatedEntityCollectionResponse,
    PaginatedEntityResponseDTO
} from "../../objects/interface";
import { IExtensions } from ".";
import { Comedian } from "../../objects/class/comedian/Comedian";
import { QueryHelper } from "../../objects/class/query/QueryHelper";
import { EntityType } from "../../objects/enum";

const columnSets: {
    updateScores: ColumnSet | null;
    addAll: ColumnSet | null;
    updateSocial: ColumnSet | null;
    updateHashes: ColumnSet | null;
} = {
    updateScores: null,
    addAll: null,
    updateSocial: null,
    updateHashes: null,
};

export class ComediansRepository {
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
            { table: "comedians" },
        );
        columnSets.updateSocial = new pgp.helpers.ColumnSet(
            [
                "?id",
                "instagram_account",
                "tiktok_account",
                "youtube_account",
                "youtube_followers",
                "instagram_followers",
                "tiktok_followers",
                "popularity_score",
                "website",
            ],
            { table: "comedians" },
        );
        columnSets.addAll = new pgp.helpers.ColumnSet(["name", "uuid"], {
            table: "comedians",
        });
        columnSets.updateHashes = new pgp.helpers.ColumnSet(
            ["?id", "uuid"],
            { table: "comedians" },
        );
    }

    createTable(): Promise<null> {
        return this.db.none(sql.createTable);
    }

    async getAll(params: QueryHelper): Promise<PaginatedEntityCollectionResponse> {
        const queryFile = params.getQuery(sql, EntityType.Comedian)
        const filters = params.asComedianQueryFilters();
        return this.db
            .oneOrNone(queryFile, filters)
            .then((result: PaginatedEntityCollectionResponseDTO<ComedianDTO> | null) => {
                return {
                    entities: result ? result.response.data.map((result: ComedianDTO) => new Comedian(result)) : [],
                    total: result ? result.response.total : 0
                }
            });
    }

    async getByName(name: string, params: QueryHelper): Promise<PaginatedEntityResponse> {
        const queryFile = params.getQuery(sql, EntityType.Comedian)
        const filters = params.asComedianQueryFilters();
        return this.db
            .oneOrNone(queryFile, filters)
            .then((result: PaginatedEntityResponseDTO<ComedianDTO> | null) => {
                if (result) {
                    return {
                        entity: new Comedian(result.response.data),
                        total: result.response.total
                    }
                }
                throw new Error(`No comedian found with name: ${name}`)
            });
    }

    async getById(id: number, params: QueryHelper): Promise<PaginatedEntityResponse> {
        const queryFile = params.getQuery(sql, EntityType.Comedian)
        const filters = params.asComedianQueryFilters();
        return this.db
            .oneOrNone(queryFile, filters)
            .then((result: PaginatedEntityResponseDTO<ComedianDTO> | null) => {
                if (result) {
                    return {
                        entity: new Comedian(result.response.data),
                        total: result.response.total
                    }
                }
                throw new Error(`No comedian found with id: ${id}`)
            });
    }

    async getAllFavorites(
        userId: number,
        params: QueryHelper
    ): Promise<PaginatedEntityCollectionResponse> {
        const queryFile = params.getQuery(sql, EntityType.Comedian)
        const filters = params.asComedianQueryFilters();
        return this.db
            .oneOrNone(queryFile, filters)
            .then((result: PaginatedEntityCollectionResponseDTO<ComedianDTO> | null) => {
                return {
                    entities: result ? result.response.data.map((result: ComedianDTO) => new Comedian(result)) : [],
                    total: result ? result.response.total : 0
                }
            });
    }

    async getTrendingComedians(total: number): Promise<Comedian[]> {
        return this.db
            .any(sql.getTrending, {
                total,
            })
            .then((response: ComedianDTO[] | null) => response ? response.map((item: ComedianDTO) => new Comedian(item)) : []);

    }

    addAll(all: ComedianDTO[]): Promise<null> {
        const batchInsert =
            this.pgp.helpers.insert(all, columnSets.addAll) +
            " ON CONFLICT (uuid) DO NOTHING";
        return this.db.none(batchInsert);
    }

    updateScores(scores: PopularityScoreIODTO[] | null): Promise<null> {
        if (scores == null) return providedPromiseResponse(null);

        const update =
            this.pgp.helpers.update(scores, columnSets.updateScores) +
            " WHERE v.id = t.id";
        return this.db.none(update);
    }

    updateSocialData(payload: SocialDataDTO): Promise<boolean | null> {
        const update =
            this.pgp.helpers.update([payload], columnSets.updateSocial) +
            " WHERE v.id = t.id RETURNING 1";
        return this.db.oneOrNone(update);
    }

}
