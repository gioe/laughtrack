import { ColumnSet, IDatabase, IMain } from "pg-promise";
import { clubs as sql } from "../sql";
import {
    GroupedSocialDataDTO,
    PopularityScoreIODTO,
    GetCitiesResponseDTO,
    SearchParams,
} from "../../objects/interfaces";
import { providedPromiseResponse } from "../../util/promiseUtil";
import { IExtensions } from ".";
import { ClubDTO } from "../../objects/classes/club/club.interface";
import { Club } from "../../objects/classes/club/Club";

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
                "base_url",
                "scraping_page_url",
                "scraping_config",
                "popularity_score",
            ],
            { table: "clubs" },
        );
    }

    // Creates the table;
    createTable(): Promise<null> {
        return this.db.none(sql.create);
    }

    addAll(all: ClubDTO[]): Promise<null> {
        const batchInsert =
            this.pgp.helpers.insert(all, columnSets.addAll) +
            `ON CONFLICT (name) DO UPDATE SET scraping_config = EXCLUDED.scraping_config`;
        return this.db.none(batchInsert);
    }

    // Tries to find a club from id;
    async getByName(name: string): Promise<Club | null> {
        return this.db
            .oneOrNone(sql.getByName, { name })
            .then((response: ClubDTO | null) =>
                response ? new Club(response) : null,
            );
    }

    async getAllCities(): Promise<string[]> {
        return this.db
            .any(sql.getCities)
            .then((response: GetCitiesResponseDTO[]) =>
                response.map((item: GetCitiesResponseDTO) => item.city),
            );
    }

    // Returns all club records;
    async getAll(searchParams: SearchParams): Promise<Club[]> {
        return this.db
            .any("SELECT * FROM clubs")
            .then((response: ClubDTO[] | null) =>
                response ? response.map((dto: ClubDTO) => new Club(dto)) : [],
            );
    }

    getAllPopularityData(): Promise<GroupedSocialDataDTO[] | null> {
        return this.db.any(sql.getAllShowPopularityData);
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
            .manyOrNone(sql.getAllInCity, {
                city,
            })
            .then((response: ClubDTO[] | null) =>
                response ? response.map((dto: ClubDTO) => new Club(dto)) : [],
            );
    }


}
