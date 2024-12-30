import {
    Favoritable,
    Entity
} from "../../interface";
import { ShowDTO } from "../show/show.interface";
import { SocialDataDTO } from "../socialData/socialData.interface";

// Client
export interface ClubInterface
    extends
    Favoritable,
    Entity {
    website: string;
    city: string;
    address: string;
    zipCode: string;
    showCount?: number;
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
    show_count?: number
}

export interface ClubActivityDTO {
    name: string,
    count: number
}



export interface PaginatedClubResponseDTO {
    response: {
        data: ClubDTO[],
        total: number
    }
}
