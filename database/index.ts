import pgPromise from "pg-promise";
import { Diagnostics } from "./diagostics"; // optional diagnostics
import { IInitOptions, IDatabase, IMain } from "pg-promise";
import {
    IExtensions,
    UsersRepository,
    ComediansRepository,
    ClubsRepository,
    ShowsRepository,
    FavoritesRepository,
    TagsRepository,
    LineupItemRepository,
    CityRepository
} from "./repos";
import { createSingleton } from "../util/singletonUtil";

type ExtendedProtocol = IDatabase<IExtensions> & IExtensions;

interface IDatabaseScope {
    db: ExtendedProtocol;
    pgp: IMain;
}

export function getDB(): IDatabaseScope {
    return createSingleton<IDatabaseScope>('laughtrack-db', () => {
        const initOptions: IInitOptions<IExtensions> = {
            extend(obj: ExtendedProtocol) {
                obj.users = new UsersRepository(obj, pgp);
                obj.clubs = new ClubsRepository(obj, pgp);
                obj.comedians = new ComediansRepository(obj, pgp);
                obj.shows = new ShowsRepository(obj, pgp);
                obj.favorites = new FavoritesRepository(obj, pgp);
                obj.tags = new TagsRepository(obj, pgp);
                obj.lineupItems = new LineupItemRepository(obj, pgp);
                obj.cities = new CityRepository(obj, pgp);
            },
        };

        const pgp: IMain = pgPromise(initOptions);

        const db: ExtendedProtocol = pgp({
            user: process.env.LOCAL_DB_USER as string,
            database: process.env.DB_NAME as string,
            password: process.env.LOCAL_DB_PASSWORD as string,
            max: 5,
        });

        Diagnostics.init(initOptions);

        return {
            db,
            pgp
        };
    });
}
