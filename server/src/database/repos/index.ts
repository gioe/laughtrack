import {ClubsRepository} from './clubs.js';
import {ComediansRepository} from './comedians.js';
import {ShowsRepository} from './shows.js';
import {UsersRepository} from './users.js';
import {SearchRepository} from './search.js';

// Database Interface Extensions:
interface IExtensions {
    users: UsersRepository,
    clubs: ClubsRepository,
    comedians: ComediansRepository,
    shows: ShowsRepository
    search: SearchRepository

}

export {
    IExtensions,
    UsersRepository,
    ClubsRepository,
    ComediansRepository,
    ShowsRepository, 
    SearchRepository
};