import {
    Favoritable,
    Scrapable,
    Entity
} from "../../interface";
import { ShowDTO } from "../show/show.interface";
import { SocialDataDTO } from "../socialData/socialData.interface";

// Client
export interface ClubInterface
    extends
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
    tags?: number[];
    is_Favorite?: boolean
}



export interface PaginatedClubResponseDTO {
    response: {
        data: ClubDTO[],
        total: number
    }
}
