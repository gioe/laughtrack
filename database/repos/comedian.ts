import { ColumnSet, IDatabase, IMain } from "pg-promise";
import { comedian as sql } from "../sql";
import { providedPromiseResponse } from "../../util/promiseUtil";
import { ComedianDTO, ComedianInterface } from "../../objects/classes/comedian/comedian.interface";
import { PopularityScoreIODTO, SearchParams, SocialDataDTO } from "../../objects/interfaces";
import { IExtensions } from ".";
import { Comedian } from "../../objects/classes/comedian/Comedian";

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

    // Creates the table;
    createTable(): Promise<null> {
        return this.db.none(sql.createTable);
    }

    // Tries to find a comedian from name;
    async getByName(name: string): Promise<Comedian | null> {
        return this.db
            .oneOrNone(sql.getByName, {
                name,
            })
            .then((response: ComedianDTO | null) =>
                response ? new Comedian(response) : null,
            );
    }

    async tag(id: number, tagIds: string[]): Promise<null> {
        return this.db
            .none("", {
                showId: +id,
            })
    }

    async getById(id: number, searchParams: SearchParams): Promise<Comedian | null> {
        return this.db
            .oneOrNone(sql.getById, {
                id,
            })
            .then((response: ComedianDTO | null) =>
                response ? new Comedian(response) : null,
            );
    }

    // Returns all comedian records;
    all(): Promise<ComedianDTO[] | null> {
        return this.db.any(sql.getAll);
    }

    async getAllFavorites(
        userId: number,
        searchParams: SearchParams
    ): Promise<ComedianInterface[]> {
        return this.db
            .any(sql.getAll, {
                user_id: userId,
            })
            .then((response: ComedianDTO[] | null) => response ? response.map((item: ComedianDTO) => new Comedian(item)) : []);
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

    writeHashes(all: ComedianDTO[]): Promise<null> {
        const batchInsert =
            this.pgp.helpers.update(all, columnSets.updateHashes) +
            "WHERE v.id = t.id";
        return this.db.none(batchInsert);
    }
    // Returns all club records;
    async getAll(searchParams: SearchParams): Promise<Comedian[]> {
        return this.db
            .any("SELECT * FROM comedians")
            .then((response: ComedianDTO[] | null) =>
                response ? response.map((dto: ComedianDTO) => new Comedian(dto)) : [],
            );
    }

}
