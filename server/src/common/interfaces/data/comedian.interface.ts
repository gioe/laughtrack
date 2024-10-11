import { LineupItemDTO } from "./lineupItem.interface.js";
import { GetSocialDataDTO } from "./socialData.interface.js";

export interface GetComediansDTO {
    userId?: number;
    query?: string;
    sort?: string;
}

export interface CreateComedianDTO {
    name: string;
}

export interface GetComedianResponseDTO {
    id: number;
    name: string;
    social_data: GetSocialDataDTO;
    dates: GetDateDTO[];
    favorite_id?: number;
}

export interface GetDateDTO {
    id: number;
    city: string;
    lineup: LineupItemDTO[]
    club_name: string;
    club_id: number;
    popularity_score: number;
    date_time: Date;
    ticket_link: string
}