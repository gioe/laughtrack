import { Favoritable, Entity } from "../../interface";
import { ShowDTO } from "../show/show.interface";
import { SocialDataDTO } from "../socialData/socialData.interface";

// Client
export interface ClubInterface extends Favoritable, Entity {
    website: string;
    city: string;
    address: string;
    zipCode: string;
    showCount?: number;
}

// DB
export interface ClubDTO {
    id?: number;
    imageUrl: string;
    name?: string;
    website?: string;
    address?: string;
    city?: string;
    state?: string;
    zipCode: string | null;
    social_data?: SocialDataDTO;
    dates?: ShowDTO[];
    is_Favorite?: boolean;
    show_count?: number;
    active_comedian_count?: number;
    phone_number?: string;
}

export interface PaginatedClubResponseDTO {
    response: {
        data: ClubDTO[];
        total: number;
    };
}
