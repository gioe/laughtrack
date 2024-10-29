import pgPromise from 'pg-promise';
import { Diagnostics } from './diagostics'; // optional diagnostics
import { IInitOptions, IDatabase, IMain } from 'pg-promise';
import {
  IExtensions,
  UsersRepository,
  ComediansRepository,
  ClubsRepository,
  ShowsRepository,
  SearchRepository,
  FavoritesRepository,
  LineupsRepository,
  TagsRepository,
  GroupsRepository
} from './repos';

type ExtendedProtocol = IDatabase<IExtensions> & IExtensions;

// pg-promise initialization options:
const initOptions: IInitOptions<IExtensions> = {
  // Extending the database protocol with our custom repositories;
  // API: http://vitaly-t.github.io/pg-promise/global.html#event:extend
  extend(obj: ExtendedProtocol, dc: any) {
    // Database Context (dc) is mainly needed for extending multiple databases with different access API.

    // Do not use 'require()' here, because this event occurs for every task and transaction being executed,
    // which should be as fast as possible.
    obj.users = new UsersRepository(obj, pgp);
    obj.clubs = new ClubsRepository(obj, pgp);
    obj.comedians = new ComediansRepository(obj, pgp);
    obj.shows = new ShowsRepository(obj, pgp);
    obj.search = new SearchRepository(obj, pgp);
    obj.favorites = new FavoritesRepository(obj, pgp);
    obj.lineups = new LineupsRepository(obj, pgp);
    obj.tags = new TagsRepository(obj, pgp);
    obj.groups = new GroupsRepository(obj, pgp)
  }
};

// Initializing the library:
const pgp: IMain = pgPromise(initOptions);

// Creating the database instance with extensions:
const db: ExtendedProtocol = pgp({
  user: process.env.LOCAL_DB_USER as string,
  database: process.env.DB_NAME as string,
  password: process.env.LOCAL_DB_PASSWORD as string,
  max: 5
});

// Initializing optional diagnostics:
Diagnostics.init(initOptions);


// Alternatively, you can get access to pgp via db.$config.pgp
// See: https://vitaly-t.github.io/pg-promise/Database.html#$config
export { db, pgp };