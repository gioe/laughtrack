import { Entity } from "../../interface";
import {
    SocialDataDTO,
    SocialDiscoverable,
} from "../socialData/socialData.interface";
import { ComedianLineupDTO } from "../comedian/comedianLineup.interface";
import { TicketDTO } from "../ticket/ticket.interface";

// Client
export interface ShowInterface extends Entity, SocialDiscoverable {
    name: string;
    date: Date;
    popularityScore?: number;
    clubName?: string;
    clubAddress?: string;
    lastScrapedDate?: Date;
    description?: string;
    soldOut?: boolean;
}

export interface ShowTagDTO {
    slug: string;
    name: string;
}

// DB
export interface ShowDTO {
    id: number;
    clubId: number;
    clubName?: string;
    clubCity?: string | null;
    clubState?: string | null;
    date: Date;
    tickets?: TicketDTO[];
    name: string | null;
    socialData?: SocialDataDTO;
    lineup?: ComedianLineupDTO[];
    description?: string;
    address?: string;
    room?: string | null;
    imageUrl: string;
    soldOut?: boolean;
    distanceMiles?: number | null;
    timezone?: string | null;
    // PUBLIC-visibility tags only — ADMIN tags are filtered at the query
    // boundary so internal taxonomy can never leak through the API.
    tags?: ShowTagDTO[];
}

export interface PaginatedShowResponseDTO {
    response: {
        data: ShowDTO[];
        total: number;
    };
}
