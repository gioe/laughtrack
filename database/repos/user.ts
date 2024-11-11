import { IDatabase, IMain } from "pg-promise";
import { user as sql } from "../sql";
import { UserDTO, UserInterface } from "../../objects/interfaces";
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

    // Adds a new user, and returns the new object;
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

    // Tries to find a user from id;
    async findById(id: number): Promise<UserInterface> {
        return this.db.oneOrNone("SELECT * FROM users WHERE id = $1", +id)
            .then((response: UserInterface | null) => {
                if (response) return response
                throw new Error(`No user found with id ${id}`)
            });
    }

    // Tries to find a user from name;
    async getUserByEmail(email: string): Promise<UserInterface> {
        return this.db.oneOrNone("SELECT * FROM users WHERE email = $1", email)
            .then((response: UserInterface | null) => {
                if (response) return response
                throw new Error(`No user found with email ${email}`)
            });
    }

    // Tries to find a user from name;
    async checkForExistence(email: string): Promise<boolean> {
        return this.db.oneOrNone("SELECT * FROM users WHERE email = $1", email)
            .then((response: UserInterface | null) => {
                if (response) return true
                return false
            });
    }

    // Returns all user records;
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
