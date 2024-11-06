import {
    Taggable,
    TagInterface,
    Entity,
} from "../../interfaces";
import { SocialDataDTO, SocialDiscoverable } from "../../interfaces/socialData.interface";
import { ComedianDTO, ComedianInterface } from "../comedian/comedian.interface";

// Client
export interface ShowInterface extends Taggable, Entity, SocialDiscoverable {
    name: string;
    dateTime: Date;
    lineup: ComedianInterface[];
    popularityScore?: number;
    clubName?: string;
    price: number;
    ticketLink: string;
}

// DB
export interface ShowDTO {
    club_name?: string;
    club_id: number;
    date_time: Date;
    ticket_link: string;
    name: string;
    price: string;
    social_data?: SocialDataDTO;
    tags?: TagInterface[]
    lineup?: ComedianDTO[]
    id?: number;
}
