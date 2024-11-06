import {
    Taggable,
    SocialDataDTO,
    ShowProvider,
    Favoritable,
    ImageRepresentable,
    Scrapable,
    TagDTO,
    Entity
} from "../../interfaces";
import { ShowDTO } from "../show/show.interface";

// Client
export interface ClubInterface
    extends ShowProvider,
    Taggable,
    Favoritable,
    ImageRepresentable,
    Scrapable,
    Entity {
    baseUrl: string;
    city: string;
    address: string;
    zipCode: string;
}

// DB
export interface ClubDTO {
    id: number;
    name: string;
    city: string;
    address: string;
    base_url: string;
    scraping_page_url: string;
    zip_code: string;
    social_data?: SocialDataDTO;
    dates?: ShowDTO[];
    tags?: TagDTO[];
    is_Favorite?: boolean
}
