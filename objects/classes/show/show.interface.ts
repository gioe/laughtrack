import {
    Taggable,
    TagInterface,
    Entity,
} from "../../interfaces";
import { SocialDataDTO, SocialDiscoverable } from "../../interfaces/socialData.interface";
import { Comedian } from "../comedian/Comedian";
import { ComedianDTO } from "../comedian/comedian.interface";
import { Ticket } from "../ticket/Ticket";
import { TicketDTO } from "../ticket/ticket.interface";

// Client
export interface ShowInterface extends Taggable, Entity, SocialDiscoverable {
    name: string;
    dateTime: Date;
    lineup: Comedian[];
    popularityScore?: number;
    clubName?: string;
    clubId: number;
    ticket: Ticket;
    lastScrapeTime?: Date
}

// DB
export interface ShowDTO {
    club_name?: string;
    club_id: number;
    date_time: Date;
    ticket: TicketDTO;
    name: string;
    social_data?: SocialDataDTO;
    tags?: TagInterface[]
    lineup?: ComedianDTO[]
    id?: number;
    last_scrape_time?: Date
}
