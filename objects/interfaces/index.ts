import { BannerProviderInterface } from "./bannerProvider.interface";
import { CityInterface, GetCitiesResponseDTO } from "./city.interface";
import { ImageRepresentable } from "./imageRepresentable.interface";
import { Favoritable, FavoriteDTO } from "./favoritable.interface";
import { FilterOption } from "./filter.interface";
import { Scrapable } from "./scrape.interface";
import { ModalState } from "./modalState.interface";
import { Paginated, PaginationData } from "./paginated.interface";
import { ScrapingArgs, ScrapingOutput, ClubScraper } from "./scrape.interface";
import { SearchParams } from "./searchParams.interface";
import { ShowProvider } from "./showProvider.interface";
import { Identifiable } from "./identifable.interface"
import {
    SocialDataInterface,
    SocialDiscoverable,
    SocialDataDTO,
    GroupedSocialDataDTO,
    PopularityScoreIODTO,
} from "./socialData.interface";
import { SortOptionInterface } from "./sortOption.interface";
import {
    TagInterface,
    TagDTO
} from "./tag.interface";
import { Taggable } from "./taggable.interface";
import { AuthToken } from "./token.interface";
import { UserInterface, UserDTO } from "./user.interface";
import { Entity } from "./entity.interface"

export type {
    BannerProviderInterface,
    ModalState,
    Paginated,
    ScrapingArgs,
    ScrapingOutput,
    CityInterface,
    SearchParams,
    ShowProvider,
    SocialDataInterface,
    SortOptionInterface,
    TagInterface,
    Taggable,
    AuthToken,
    UserInterface,
    UserDTO,
    SocialDiscoverable,
    PopularityScoreIODTO,
    Favoritable,
    FilterOption,
    GroupedSocialDataDTO,
    SocialDataDTO,
    GetCitiesResponseDTO,
    FavoriteDTO,
    PaginationData,
    ClubScraper,
    TagDTO,
    Identifiable,
    ImageRepresentable,
    Scrapable,
    Entity
};
