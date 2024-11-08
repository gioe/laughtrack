import { ClubsRepository } from "./clubs";
import { ComediansRepository } from "./comedians";
import { ShowsRepository } from "./shows";
import { UsersRepository } from "./users";
import { SearchRepository } from "./search";
import { FavoritesRepository } from "./favorites";
import { TagsRepository } from "./tags";
import { LineupsRepository } from "./lineups";

// Database Interface Extensions:
export interface IExtensions {
    users: UsersRepository;
    clubs: ClubsRepository;
    comedians: ComediansRepository;
    shows: ShowsRepository;
    search: SearchRepository;
    favorites: FavoritesRepository;
    tags: TagsRepository;
    lineups: LineupsRepository;
}

export {
    UsersRepository,
    ClubsRepository,
    ComediansRepository,
    ShowsRepository,
    SearchRepository,
    FavoritesRepository,
    TagsRepository,
    LineupsRepository
};
