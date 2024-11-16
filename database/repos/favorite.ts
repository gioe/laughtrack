import { IDatabase, IMain } from "pg-promise";
import { map } from "../sql";
import { FavoriteDTO } from "../../objects/interface";
import { IExtensions } from ".";
import { ComedianDTO } from "../../objects/class/comedian/comedian.interface";
import { Comedian } from "../../objects/class/comedian/Comedian";

export class FavoritesRepository {
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
    ) { }

    // Creates the table;
    createTable(): Promise<null> {
        return this.db.none(map.favorite.createTable);
    }

    // Adds a new user, and returns the new object;
    add(payload: FavoriteDTO): Promise<boolean> {
        return this.db.one(
            map.favorite.add,
            {
                comedian_id: payload.id,
                user_id: payload.user_id,
            },
            () => true,
        );
    }

    // Tries to delete a user by id, and returns the number of records deleted;
    async remove(payload: FavoriteDTO): Promise<boolean> {
        return this.db.result(
            map.favorite.remove,
            {
                comedian_id: payload.id,
                user_id: payload.user_id,
            },
            () => false,
        );
    }

    async findByUserId(id: number): Promise<Comedian[] | null> {
        return this.db.any(
            "SELECT * FROM favorite_comedians WHERE user_id = $1",
            +id,
        )
            .then((response: ComedianDTO[] | null) => response ? response.map((item: ComedianDTO) => new Comedian(item)) : []);
    }
}
