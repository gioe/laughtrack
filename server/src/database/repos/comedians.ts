import { ColumnSet, IDatabase, IMain } from 'pg-promise';
import { comedians as sql } from '../sql/index.js';
import { CreateComedianDTO, GetComedianResponseDTO } from '../../common/interfaces/data/comedian.interface.js';
import { ComedianInterface } from '../../common/interfaces/client/comedian.interface.js';
import { PopularityScoreIODTO, GetSocialDataDTO } from '../../common/interfaces/data/socialData.interface.js';
import { provideGenericPromiseResponse } from '../../common/util/promiseUtil.js';

var columnSets: {
    updateScores: ColumnSet | null;
    addAll: ColumnSet | null;
} = {
    updateScores: null,
    addAll: null
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
        columnSets.updateScores = new pgp.helpers.ColumnSet(['?id', 'popularity_score'], {table: 'comedians'});
        columnSets.addAll = new pgp.helpers.ColumnSet(['name' ], {table: 'comedians'});
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

    getAllFavorites(userId: number): Promise<GetComedianResponseDTO[] | null> {
        return this.db.any(sql.getAllFavorites, {
            user_id: userId
        });
    }

    // Returns all comedian records;
    all(): Promise<GetComedianResponseDTO[]> {
        return this.db.any('SELECT * FROM comedians ORDER BY popularity_score DESC');
    }

    allWithFavorites(userId: number): Promise<GetComedianResponseDTO[]> {
        return this.db.any(sql.getAllWithFavorites, {
            user_id: userId
        });
    }

    getTrendingComedians(): Promise<ComedianInterface[] | null> {
        return this.db.any(sql.getTrending);
    }

    addAll(all: CreateComedianDTO[]): Promise<{id: number}[]> {
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
}