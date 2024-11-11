import {
    Taggable,
    SocialDataDTO,
    ShowProvider,
    Favoritable,
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
    Scrapable,
    Entity {
    website: string;
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
    website: string;
    scraping_page_url: string;
    zip_code: string;
    social_data?: SocialDataDTO;
    dates?: ShowDTO[];
    tags?: TagDTO[];
    is_Favorite?: boolean
}



export interface PaginatedClubResponseDTO {
    response: {
        data: ClubDTO[],
        total: number
    }
}
