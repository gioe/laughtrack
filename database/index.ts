import pgPromise from "pg-promise";
import { Diagnostics } from "./diagostics"; // optional diagnostics
import { IInitOptions, IDatabase, IMain } from "pg-promise";
import { createSingleton } from "../util/singletonUtil";
import { IExtensions, PageDataRepository, ScraperRepository } from "./repository";

export type LaughtrackDatabase = IDatabase<IExtensions> & IExtensions;

interface DatabaseWrapper {
    database: LaughtrackDatabase;
    pgPromiseHelpers: IMain;
}

export function getDB(): DatabaseWrapper {
    return createSingleton<DatabaseWrapper>('laughtrack-db', () => {

        const initOptions: IInitOptions<IExtensions> = {
            extend(database: LaughtrackDatabase) {
                database.scrape = new ScraperRepository(database, pgPromiseHelpers)
                database.page = new PageDataRepository(database, pgPromiseHelpers)
            },
        };

        const pgPromiseHelpers: IMain = pgPromise(initOptions);

        const database: LaughtrackDatabase = pgPromiseHelpers({
            user: process.env.LOCAL_DB_USER as string,
            database: process.env.DB_NAME as string,
            password: process.env.LOCAL_DB_PASSWORD as string,
            max: 5,
        });

        Diagnostics.init(initOptions);

        return {
            database,
            pgPromiseHelpers
        };
    });
}
