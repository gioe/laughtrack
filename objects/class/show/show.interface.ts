import {
    Taggable,
    Entity,
} from "../../interface";
import { SocialDataDTO, SocialDiscoverable } from "../socialData/socialData.interface";
import { ComedianDTO } from "../comedian/comedian.interface";
import { Ticket } from "../ticket/Ticket";
import { TicketDTO } from "../ticket/ticket.interface";

// Client
export interface ShowInterface extends Taggable, Entity, SocialDiscoverable {
    name: string;
    date: Date;
    popularityScore?: number;
    clubName?: string;
    clubAddress?: string,
    clubId: number;
    ticket: Ticket;
    lastScrapedDate?: Date
    description?: string
}

// DB
export interface ShowDTO {
    club_name?: string;
    club_id?: number;
    date: Date;
    ticket: TicketDTO;
    name: string | null;
    social_data?: SocialDataDTO;
    tags?: number[]
    lineup?: ComedianDTO[]
    id?: number;
    last_scraped_date?: Date
    description?: string;
    club_address?: string
}

export interface PaginatedShowResponseDTO {
    response: {
        data: ShowDTO[],
        total: number
    }
}
