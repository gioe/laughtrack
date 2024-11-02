import { Comedian } from "../classes/Comedian";
import {
    ComedianInterface,
    GetSocialDataDTO,
    SocialDataInterface,
    GetTagResponseDTO,
    Taggable,
    GetComedianResponseDTO,
} from ".";

// Client
export interface ShowInterface extends Taggable {
    id: number;
    name: string;
    dateTime: Date;
    socialData: SocialDataInterface;
    lineup: ComedianInterface[];
    popularityScore?: number;
    clubName?: string;
    price: number;
    ticketLink: string;
}

export interface ShowInput {
    lineup: Comedian[];
    dateTime: Date;
    ticketLink: string;
    name: string;
    price: string;
    clubId: number;
}

// DB
export interface CreateShowDTO {
    club_id: number;
    date_time: Date;
    ticket_link: string;
    name: string;
    price: string;
}

export interface GetShowResponseDTO {
    id: number;
    price: string;
    date_time: Date;
    social_data: GetSocialDataDTO;
    name: string;
    club_name: string;
    base_url: string;
    popularity_score: number;
    lineup: GetComedianResponseDTO[];
    tags: GetTagResponseDTO[];
    ticket_link: string;
}
