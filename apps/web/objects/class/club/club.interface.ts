import { Favoritable, Entity } from "../../interface";
import { ShowDTO } from "../show/show.interface";
import { SocialDataDTO } from "../socialData/socialData.interface";

// Client
export interface ClubInterface extends Favoritable, Entity {
    website: string;
    city: string;
    state: string;
    address: string;
    zipCode: string;
    showCount?: number;
}

// DB
export type ClubHours = Record<string, string>;

export interface ClubDTO {
    id?: number;
    imageUrl: string;
    name?: string;
    website?: string;
    address?: string;
    city?: string;
    state?: string;
    zipCode: string | null;
    socialData?: SocialDataDTO;
    dates?: ShowDTO[];
    isFavorite?: boolean;
    showCount?: number;
    activeComedianCount?: number;
    phoneNumber?: string;
    description?: string;
    hours?: unknown;
    distanceMiles?: number | null;
    chainId?: number | null;
    chainName?: string | null;
    chainSlug?: string | null;
    // When this club represents a multi-location chain in the search grid (the
    // chain's "flagship" card), the number of locations in that chain. Null for
    // standalone clubs and for individual locations shown under a chain filter.
    chainLocationCount?: number | null;
    clubType?: string;
}

export interface PaginatedClubResponseDTO {
    response: {
        data: ClubDTO[];
        total: number;
    };
}
