import {
    Taggable,
    TagInterface,
    Entity,
} from "../../interface";
import { SocialDataDTO, SocialDiscoverable } from "../../interface/socialData.interface";
import { Comedian } from "../comedian/Comedian";
import { ComedianDTO } from "../comedian/comedian.interface";
import { Ticket } from "../ticket/Ticket";
import { TicketDTO } from "../ticket/ticket.interface";

// Client
export interface ShowInterface extends Taggable, Entity, SocialDiscoverable {
    name: string;
    date: Date;
    lineup: Comedian[];
    popularityScore?: number;
    clubName?: string;
    clubId: number;
    ticket: Ticket;
    scraped?: Date
}

// DB
export interface ShowDTO {
    club_name?: string;
    club_id: number;
    date: Date;
    ticket: TicketDTO;
    name: string;
    social_data?: SocialDataDTO;
    tags?: TagInterface[]
    lineup?: ComedianDTO[]
    id?: number;
    scraped?: Date
}

export interface PaginatedShowResponseDTO {
    response: {
        data: ShowDTO[],
        total: number
    }
}
