import { ColumnSet, IDatabase, IMain } from 'pg-promise';
import { comedians as sql } from '../sql/index.js';
import { provideGenericPromiseResponse } from '../../common/util/promiseUtil.js';
import { ComedianInterface, CreateComedianDTO, GetComedianResponseDTO } from '../../common/models/interfaces/comedian.interface.js';
import { GetSocialDataDTO, PopularityScoreIODTO, UpdateSocialDataDTO } from '../../common/models/interfaces/socialData.interface.js';

var columnSets: {
    updateScores: ColumnSet | null;
    addAll: ColumnSet | null;
    updateData: ColumnSet | null;
} = {
    updateScores: null,
    addAll: null,
    updateData: null
}

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
    constructor(private db: IDatabase<any>, private pgp: IMain) {
        this.createTable();
        columnSets.updateScores = new pgp.helpers.ColumnSet(['?id', 'popularity_score'], { table: 'comedians' });
        columnSets.updateData = new pgp.helpers.ColumnSet(['?id', 'instagram_account', 'tiktok_account',
            'youtube_account', 'youtube_followers', 'instagram_followers', 'tiktok_followers', 'popularity_score', 'website'], { table: 'comedians' });
        columnSets.addAll = new pgp.helpers.ColumnSet(['name'], { table: 'comedians' });
    }

    // Creates the table;
    createTable(): Promise<null> {
        return this.db.none(sql.create);
    }

    // Tries to find a comedian from name;
    findByName(name: string): Promise<GetComedianResponseDTO | null> {
        return this.db.oneOrNone(sql.getByName, {
            name
        });
    }

    // Returns all comedian records;
    all(): Promise<GetComedianResponseDTO[] | null> {
        return this.db.any(sql.getAllWithSocialData)
    }

    getAllFavorites(userId: number): Promise<GetComedianResponseDTO[] | null> {
        return this.db.any(sql.getAllFavorites, {
            user_id: userId
        });
    }

    allWithFavorites(userId: number): Promise<GetComedianResponseDTO[] | null> {
        return this.db.any(sql.getAllWithFavoritesAndSocialData, {
            user_id: userId
        });
    }

    getTrendingComedians(): Promise<ComedianInterface[] | null> {
        return this.db.any(sql.getTrending);
    }

    addAll(all: CreateComedianDTO[]): Promise<{ id: number }[]> {
        const batchInsert = this.pgp.helpers.insert(all, columnSets.addAll) + ' ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id';
        return this.db.any(batchInsert)
    }

    getAllSocialData(): Promise<GetSocialDataDTO[] | null> {
        return this.db.any(sql.getAllSocialData)
    }

    updateScores(scores: PopularityScoreIODTO[] | null): Promise<null> {
        if (scores == null) return provideGenericPromiseResponse(null)

        const update = this.pgp.helpers.update(scores, columnSets.updateScores) + ' WHERE v.id = t.id';
        return this.db.none(update)
    }

    updateSocialData(payload: UpdateSocialDataDTO): Promise<boolean | null> {
        const update = this.pgp.helpers.update([payload], columnSets.updateData) + ' WHERE v.id = t.id RETURNING 1';
        return this.db.oneOrNone(update)
    }
}