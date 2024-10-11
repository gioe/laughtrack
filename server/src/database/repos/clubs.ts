import {ColumnSet, IDatabase, IMain} from 'pg-promise';
import {clubs as sql} from '../sql/index.js';
import { 
    CreateClubDTO, 
    GetCitiesResponseDTO, 
    GetClubDTO, 
} from '../../common/models/interfaces/club.interface.js';
import { provideGenericPromiseResponse } from '../../common/util/promiseUtil.js';
import { GroupedPopularityScoreDTO, PopularityScoreIODTO } from '../../common/models/interfaces/socialData.interface.js';

var columnSets: {
    updateScores: ColumnSet | null;
    addAll: ColumnSet | null;
} = {
    updateScores: null,
    addAll: null
}

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
    constructor(private db: IDatabase<any>, private pgp: IMain) {
          this.createTable();
          columnSets.updateScores = new pgp.helpers.ColumnSet(['?id', 'popularity_score'], {table: 'clubs'});
          columnSets.addAll = new pgp.helpers.ColumnSet(['name', 'city', 'zip_code', 'address',
            'base_url', 'schedule_page_url', 'timezone', 'scraping_config', 'popularity_score'
          ], {table: 'clubs'});
    }

    // Creates the table;
    createTable(): Promise<null> {
        return this.db.none(sql.create);
    }

    addAll(all: CreateClubDTO[]): Promise<null> {
        const batchInsert = this.pgp.helpers.insert(all, columnSets.addAll) + `ON CONFLICT (name) DO UPDATE SET scraping_config = EXCLUDED.scraping_config`
        return this.db.none(batchInsert)
    }

    // Tries to find a club from id;
    getByName(name: string): Promise<GetClubDTO | null> {
        return this.db.oneOrNone(sql.getByName, {
            name,
        });
    }
    
    getAllCities(): Promise<GetCitiesResponseDTO[]> {
        return this.db.any(sql.getCities);
    }

    // Returns all club records;
    all(): Promise<GetClubDTO[] | null> {
        return this.db.any('SELECT * FROM clubs')
    }

    getAllPopularityData(): Promise<GroupedPopularityScoreDTO[] | null> {
        return this.db.any(sql.getAllShowPopularityData)
    }

    updateScores(scores: PopularityScoreIODTO[] | null): Promise<null> {
        if (scores == null) return provideGenericPromiseResponse(null)

        const update = this.pgp.helpers.update(scores, columnSets.updateScores) + ' WHERE v.id = t.id';

        return this.db.none(update)
    }

}