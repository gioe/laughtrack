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

// DB
export interface ShowDTO {
    id: number;
    clubName?: string;
    date: Date;
    tickets?: TicketDTO[];
    name: string | null;
    social_data?: SocialDataDTO;
    lineup?: ComedianLineupDTO[];
    description?: string;
    address?: string;
    imageUrl: string;
    soldOut?: boolean;
}

export interface PaginatedShowResponseDTO {
    response: {
        data: ShowDTO[];
        total: number;
    };
}
