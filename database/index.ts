import pgPromise from "pg-promise";
import { Diagnostics } from "./diagostics"; // optional diagnostics
import { IInitOptions, IDatabase, IMain } from "pg-promise";
import {
    IExtensions,
} from "./repos";
import { createSingleton } from "../util/singletonUtil";

export type LaughtrackDatabase = IDatabase<IExtensions> & IExtensions;

interface DatabaseWrapper {
    database: LaughtrackDatabase;
    pgPromiseHelpers: IMain;
}

export function getDB(): DatabaseWrapper {
    return createSingleton<DatabaseWrapper>('laughtrack-db', () => {

        const initOptions: IInitOptions<IExtensions> = {
            // eslint-disable-next-line @typescript-eslint/no-empty-function
            extend(database: LaughtrackDatabase) {
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
