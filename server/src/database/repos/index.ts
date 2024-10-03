import {ClubsRepository} from './clubs.js';
import {ComediansRepository} from './comedians.js';
import {ShowsRepository} from './shows.js';
import {UsersRepository} from './users.js';
import {SearchRepository} from './search.js';
import {LineupsRepository} from './lineups.js';
import {FavoritesRepository} from './favorites.js';

// Database Interface Extensions:
interface IExtensions {
    users: UsersRepository,
    clubs: ClubsRepository,
    comedians: ComediansRepository,
    shows: ShowsRepository,
    search: SearchRepository,
    favorites: FavoritesRepository
    lineups: LineupsRepository
}

export {
    IExtensions,
    UsersRepository,
    ClubsRepository,
    ComediansRepository,
    ShowsRepository, 
    SearchRepository,
    LineupsRepository,
    FavoritesRepository
};