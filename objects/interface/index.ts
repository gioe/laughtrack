import { Favoritable, FavoriteDTO } from "./favoritable.interface";
import { Scrapable } from "./scrape.interface";
import { ModalState } from "./modalState.interface";
import { Paginated, PaginationData } from "./paginated.interface";
import { ScrapingArgs, ScrapingOutput, ClubScraper } from "./scrape.interface";
import { LineupItemDTO } from "./lineup.interface";
import { DatabaseIdentifiable } from "./identifable.interface"
import { SelectableItem } from "./selectableItem"
import { EntityContainer } from "./entityContainer.interface";
import { RepositoryInterface } from "./repository.interface"
import {
    PaginatedEntityResponse,
    PaginatedEntityResponseDTO,
    PaginatedEntityDTO
} from "./paginatedEntity.interface";
import { SlugInterface } from "./slug.interface";
import { SortOptionInterface } from "./sortOption.interface";
import {
    TagInterface,
} from "./tag.interface";
import { Taggable } from "./taggable.interface";
import { AuthToken } from "./token.interface";
import { UserInterface, UserDTO } from "./user.interface";
import { Entity } from "./entity.interface"
import { ButtonData } from "./buttonData.interface"
import { BannerRepresentable } from "./bannerRepresentable.interface"

export type {
    SelectableItem,
    DatabaseIdentifiable,
    ButtonData,
    BannerRepresentable,
    ModalState,
    Paginated,
    ScrapingArgs,
    ScrapingOutput,
    SlugInterface,
    SortOptionInterface,
    TagInterface,
    Taggable,
    AuthToken,
    UserInterface,
    UserDTO,
    Favoritable,
    FavoriteDTO,
    PaginationData,
    ClubScraper,
    Scrapable,
    Entity,
    LineupItemDTO,
    PaginatedEntityResponse,
    PaginatedEntityResponseDTO,
    PaginatedEntityDTO,
    RepositoryInterface,
    EntityContainer,
};

