import { ClubsRepository } from "./clubs";
import { ComediansRepository } from "./comedians";
import { ShowsRepository } from "./shows";
import { UsersRepository } from "./users";
import { SearchRepository } from "./search";
import { LineupsRepository } from "./lineups";
import { FavoritesRepository } from "./favorites";
import { TagsRepository } from "./tags";
import { GroupsRepository } from "./groups";

// Database Interface Extensions:
export interface IExtensions {
    users: UsersRepository;
    clubs: ClubsRepository;
    comedians: ComediansRepository;
    shows: ShowsRepository;
    search: SearchRepository;
    favorites: FavoritesRepository;
    lineups: LineupsRepository;
    tags: TagsRepository;
    groups: GroupsRepository;
}

export {
    UsersRepository,
    ClubsRepository,
    ComediansRepository,
    ShowsRepository,
    SearchRepository,
    LineupsRepository,
    FavoritesRepository,
    TagsRepository,
    GroupsRepository,
};
