import { IDatabase, IMain } from 'pg-promise';
import { users as sql } from '../sql';
import { CreateUserDTO } from '../../interfaces';

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
    constructor(private db: IDatabase<any>, private pgp: IMain) {
        this.createTable();
    }

    // Creates the table;
    createTable(): Promise<null> {
        return this.db.none(sql.create);
    }

    // Adds a new user, and returns the new object;
    add(user: CreateUserDTO): Promise<any> {
        return this.db.one(sql.add, {
            email: user.email,
            role: user.role,
            password: user.password
        });
    }

    // Tries to find a user from id;
    findById(id: number): Promise<any | null> {
        return this.db.oneOrNone('SELECT * FROM users WHERE id = $1', +id);
    }

    // Tries to find a user from name;
    findByEmail(email: string): Promise<any | null> {
        return this.db.oneOrNone('SELECT * FROM users WHERE email = $1', email);
    }

    // Tries to find a user from name;
    checkForExistence(email: string): Promise<any | null> {
        return this.db.oneOrNone('SELECT * FROM users WHERE email = $1', email);
    }

    // Returns all user records;
    all(): Promise<any[]> {
        return this.db.any('SELECT * FROM users');
    }

    // Returns the total number of users;
    total(): Promise<number> {
        return this.db.one('SELECT count(*) FROM users', [], (a: { count: string }) => +a.count);
    }
}