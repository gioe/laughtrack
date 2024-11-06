import { ColumnSet, IDatabase, IMain } from "pg-promise";
import { comedians as sql } from "../sql";
import { providedPromiseResponse } from "../../util/promiseUtil";
import { SearchParams } from "../../objects/interfaces/searchParams.interface";
import { ComedianDTO, ComedianInterface } from "../../objects/classes/comedian/comedian.interface";
import { PopularityScoreIODTO, SocialDataDTO } from "../../objects/interfaces";
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
        columnSets.addAll = new pgp.helpers.ColumnSet(["name", "uuid_id"], {
            table: "comedians",
        });
        columnSets.updateHashes = new pgp.helpers.ColumnSet(
            ["?id", "uuid_id"],
            { table: "comedians" },
        );
    }

    // Creates the table;
    createTable(): Promise<null> {
        return this.db.none(sql.create);
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

    // Returns all comedian records;
    all(): Promise<ComedianDTO[] | null> {
        return this.db.any(sql.getAllWithSocialData);
    }

    async getAllFavorites(
        userId: number,
        searchParams?: SearchParams,
    ): Promise<ComedianInterface[]> {
        return this.db
            .any(sql.getAllFavorites, {
                user_id: userId,
            })
            .then((response: ComedianDTO[] | null) => response ? response.map((item: ComedianDTO) => new Comedian(item)) : []);
    }

    allWithFavorites(userId: number): Promise<ComedianDTO[] | null> {
        return this.db.any(sql.getAllWithFavoritesAndSocialData, {
            user_id: userId,
        });
    }

    async getTrendingComedians(): Promise<Comedian[]> {
        return this.db
            .any(sql.getTrending)
            .then((response: ComedianDTO[] | null) => response ? response.map((item: ComedianDTO) => new Comedian(item)) : []);

    }

    addAll(all: ComedianDTO[]): Promise<null> {
        const batchInsert =
            this.pgp.helpers.insert(all, columnSets.addAll) +
            " ON CONFLICT (uuid_id) DO NOTHING";
        return this.db.none(batchInsert);
    }

    getAllSocialData(): Promise<SocialDataDTO[] | null> {
        return this.db.any(sql.getAllSocialData);
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

    getIds(uuids: string[]): Promise<{ id: number }[]> {
        return this.db.any(sql.getAllIdsByUuids, [uuids]);
    }
}
