import { IDatabase, IMain } from "pg-promise";
import { user as sql } from "../sql";
import { UserDTO, UserInterface } from "../../objects/interface";
import { IExtensions } from ".";

export class UsersRepository {
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
        return this.db.none(sql.createTable);
    }

    async add(user: UserDTO): Promise<UserInterface | null> {
        return this.db.one(sql.add, {
            email: user.email,
            role: user.role,
            password: user.password,
        })
            .then((response: UserInterface | null) => {
                if (response) return response
                throw new Error(`Failed to create user: ${user}`)
            });
    }

    async getById(id: number): Promise<UserInterface> {
        return this.db.oneOrNone(sql.getById, {
            id
        }).then((response: UserInterface | null) => {
            if (response) return response
            throw new Error(`No user found with id ${id}`)
        });
    }

    async getByEmail(email: string): Promise<UserInterface> {
        return this.db.oneOrNone(sql.getByEmail, {
            email
        }).then((response: UserInterface | null) => {
            if (response) return response
            throw new Error(`No user found with email ${email}`)
        });
    }

    async checkForExistence(email: string): Promise<boolean> {
        return this.db.oneOrNone(sql.getByEmail, {
            email
        })
            .then((response: UserInterface | null) => {
                if (response) return true
                return false
            });
    }

    all(): Promise<UserInterface[]> {
        return this.db.any("SELECT * FROM users");
    }

    // Returns the total number of users;
    total(): Promise<number> {
        return this.db.one(
            "SELECT count(*) FROM users",
            [],
            (a: { count: string }) => +a.count,
        );
    }
}
