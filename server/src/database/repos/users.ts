import { IDatabase, IMain } from 'pg-promise';
import { IResult } from 'pg-promise/typescript/pg-subset.js';
import { users as sql } from '../sql/index.js';
import { CreateUserDTO } from '../../common/interfaces/data/user.interface.js';

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
        this.create();
    }

    // Creates the table;
    create(): Promise<null> {
        return this.db.none(sql.create);
    }

    // Adds a new user, and returns the new object;
    add(user: CreateUserDTO): Promise<any> {
        return this.db.one(sql.add, user.email);
    }

    // Tries to delete a user by id, and returns the number of records deleted;
    remove(id: number): Promise<number> {
        return this.db.result('DELETE FROM users WHERE id = $1', +id, (r: IResult) => r.rowCount);
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