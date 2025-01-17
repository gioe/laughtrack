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
    ticket: Ticket;
    lastScrapedDate?: Date
    description?: string
}

// DB
export interface ShowDTO {
    id: number;
    clubName?: string;
    date: Date;
    ticket: TicketDTO;
    name: string | null;
    social_data?: SocialDataDTO;
    tags?: number[]
    lineup?: ComedianDTO[]
    description?: string;
    address?: string;
    imageUrl: string;
}

export interface PaginatedShowResponseDTO {
    response: {
        data: ShowDTO[],
        total: number
    }
}
