import { LineupItemDTO } from "./lineupItem.interface.js";

export interface CreateComedianDTO {
    name: string;
}

export interface GetComedianResponseDTO {
    id: number;
    name: string;
    socialData: GetSocialDataDTO;
    dates: GetDateDTO;
}

export interface GetSocialDataDTO {
    wbesite?: string,
    tiktok_acoount?: string,
    popularity_score: number,
    tiktok_follwers?: number,
    instagram_account?: string,
    instagram_followers?: number
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