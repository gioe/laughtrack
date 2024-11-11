import { ClubsRepository } from "./club";
import { ComediansRepository } from "./comedian";
import { ShowsRepository } from "./show";
import { UsersRepository } from "./user";
import { FavoritesRepository } from "./favorite";
import { TagsRepository } from "./tag";
import { LineupItemRepository } from "./lineupItem";
import { CityRepository } from "./city";

// Database Interface Extensions:
export interface IExtensions {
    users: UsersRepository;
    clubs: ClubsRepository;
    comedians: ComediansRepository;
    shows: ShowsRepository;
    favorites: FavoritesRepository;
    tags: TagsRepository;
    lineupItems: LineupItemRepository;
    cities: CityRepository
}

export {
    UsersRepository,
    ClubsRepository,
    ComediansRepository,
    ShowsRepository,
    FavoritesRepository,
    TagsRepository,
    LineupItemRepository,
    CityRepository
};
