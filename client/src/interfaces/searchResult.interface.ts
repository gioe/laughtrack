import { MapCoordinate } from "./mapCoordinate.interface";

export interface SearchResultResponse {
    city: string;
    shows: SearchResult[];
    totalPages: number;
}

export interface SearchResult {
    id: number
    date_time: Date;
    ticket_link: string;
    club_name: string[];
    lineup: any[];
}