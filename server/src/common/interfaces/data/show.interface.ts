import {  LineupItemDTO } from "./lineupItem.interface.js";

export interface CreateShowDTO {
    club_id: number;
    date_time: Date;
    ticket_link: string;
}

export interface GetShowResponseDTO {
    id: number;
    club_id: number;
    date_time: Date;
    ticket_link: string;
    popularity_score: number;
    lineup: LineupItemDTO[];
    club_name: string;
}