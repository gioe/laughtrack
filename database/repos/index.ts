import { ClubsRepository } from "./clubs";
import { ComediansRepository } from "./comedians";
import { ShowsRepository } from "./shows";
import { UsersRepository } from "./users";
import { SearchRepository } from "./search";
import { FavoritesRepository } from "./favorites";
import { TagsRepository } from "./tags";
import { LineupItemRepository } from "./lineupItems";

// Database Interface Extensions:
export interface IExtensions {
    users: UsersRepository;
    clubs: ClubsRepository;
    comedians: ComediansRepository;
    shows: ShowsRepository;
    search: SearchRepository;
    favorites: FavoritesRepository;
    tags: TagsRepository;
    lineupItems: LineupItemRepository;
}

export {
    UsersRepository,
    ClubsRepository,
    ComediansRepository,
    ShowsRepository,
    SearchRepository,
    FavoritesRepository,
    TagsRepository,
    LineupItemRepository
};
