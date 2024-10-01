import {ColumnSet, IDatabase, IMain} from 'pg-promise';
import {IResult} from 'pg-promise/typescript/pg-subset.js';
import {IClub, IClubDetails, IClubPopularityData} from '../models.js';
import {clubs as sql} from '../sql/index.js';
import { ClubInterface, ClubPopularityScore } from '../../common/interfaces/club.interface.js';

var columnSets: {
    updateScores: ColumnSet | null;
} = {
    updateScores: null,
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
          columnSets.updateScores = new pgp.helpers.ColumnSet(['?id', 'popularity_score'], {table: 'clubs'});
    }

    // Creates the table;
    create(): Promise<null> {
        return this.db.none(sql.create);
    }

    // Drops the table;
    drop(): Promise<null> {
        return this.db.none(sql.drop);
    }

    // Removes all records from the table;
    empty(): Promise<null> {
        return this.db.none(sql.empty);
    }

    addAll(all: ClubInterface[]): Promise<null> {
        return this.db.none(sql.create);
    }

    // Adds a new club, and returns the new object;
    add(payload: ClubInterface): Promise<IClub> {
        return this.db.one(sql.add, payload.name);
    }

    // Tries to delete a club by id, and returns the number of records deleted;
    remove(id: number): Promise<number> {
        return this.db.result('DELETE FROM clubs WHERE id = $1', +id, (r: IResult) => r.rowCount);
    }

    // Tries to find a club from id;
    findById(id: number): Promise<IClub | null> {
        return this.db.oneOrNone(sql.getWithSchedule, {
            clubId: +id,
        });
    }

    // Tries to find a club from name;
    findByNameWithAllDetails(name: string): Promise<IClubDetails | null> {
        return this.db.oneOrNone(sql.getWithAllDetails, {
            name
        });
    }

    findByNameWithBaseDetails(name: string): Promise<IClubDetails | null> {
        return this.db.oneOrNone(sql.getWithBaseDetails, {
            name
        });
    }

    // Tries to find a club from city;
    findByCity(city: string): Promise<IClub[] | null> {
        return this.db.any('SELECT * FROM clubs WHERE city = $1', city);
    }

    getTrendingClubs(): Promise<IClub[] | null> {
        return this.db.any(sql.getTrending);
    }

    getAllCities(): Promise<IClub[] | null> {
        return this.db.any(sql.getCities);
    }

    // Returns all club records;
    all(): Promise<IClub[]> {
        return this.db.any('SELECT * FROM clubs');
    }

    // Returns the total number of clubs;
    total(): Promise<number> {
        return this.db.one('SELECT count(*) FROM clubs', [], (a: { count: string }) => +a.count);
    }

    delete(id: number): Promise<number> {
        return this.db.result('DELETE FROM clubs WHERE id = $1', +id, (r: IResult) => r.rowCount);
    }

    allPopularityData(): Promise<IClubPopularityData[] | null> {
        return this.db.any(sql.allPopularityData)
    }

    updateScores(scores: ClubPopularityScore[]): Promise<null> {
        const update = this.pgp.helpers.update(scores, columnSets.updateScores) + ' WHERE v.id = t.id';
        return this.db.none(update)
    }

}