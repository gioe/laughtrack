import {CitiesRepository} from './cities.js';
import {ClubsRepository} from './clubs.js';
import {ComediansRepository} from './comedians.js';
import {ShowsRepository} from './shows.js';
import {UsersRepository} from './users.js';

// Database Interface Extensions:
interface IExtensions {
    users: UsersRepository,
    cities: CitiesRepository,
    clubs: ClubsRepository,
    comedians: ComediansRepository,
    shows: ShowsRepository
}

export {
    IExtensions,
    UsersRepository,
    CitiesRepository,
    ClubsRepository,
    ComediansRepository,
    ShowsRepository
};