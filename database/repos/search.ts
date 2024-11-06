import { IDatabase, IMain } from "pg-promise";
import { shows, comedians, clubs } from "../sql";
import {
    Entity,
    SearchParams,
} from "../../objects/interfaces";
import { IExtensions } from ".";
import { EntityType } from "../../util/enum";
import { ShowDTO } from "../../objects/classes/show/show.interface";
import { Show } from "../../objects/classes/show/Show";
import { ComedianDTO } from "../../objects/classes/comedian/comedian.interface";
import { Comedian } from "../../objects/classes/comedian/Comedian";
import { ClubDTO } from "../../objects/classes/club/club.interface";
import { Club } from "../../objects/classes/club/Club";

export class SearchRepository {
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

    }

    async getSearchResults(
        type: EntityType,
        request: SearchParams,
    ): Promise<Entity[]> {
        switch (type) {
            case EntityType.Club:
                return this.getClubs(request)
            case EntityType.Show:
                return this.getShows(request)
            case EntityType.Comedian:
                return this.getComedians(request)
        }
    }

    async getShows(request: SearchParams): Promise<Show[]> {
        return this.db
            .any(shows.getSearchResults, {
                location: request.location,
                start_date: request.startDate,
                end_date: request.endDate,
            })
            .then((result: ShowDTO[] | null) =>
                result ? result.map((dto: ShowDTO) => new Show(dto)) : [],
            );
    }

    async getComedians(request: SearchParams): Promise<Comedian[]> {
        return this.db
            .any(comedians.getSearchResults, {
                location: request.location,
                start_date: request.startDate,
                end_date: request.endDate,
            })
            .then((result: ComedianDTO[] | null) =>
                result ? result.map((dto: ComedianDTO) => new Comedian(dto)) : [],
            );
    }

    async getClubs(request: SearchParams): Promise<Club[]> {
        return this.db
            .any(clubs.getSearchResults, {
                location: request.location,
                start_date: request.startDate,
                end_date: request.endDate,
            })
            .then((result: ClubDTO[] | null) =>
                result ? result.map((dto: ClubDTO) => new Club(dto)) : [],
            );
    }

}
