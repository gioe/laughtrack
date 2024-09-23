import { ShowInterface } from "./show.interface";

export interface SearchResultResponse {
    total: number;
    results: SearchResult[];
    coordinates: string[];
}


export interface SearchResult {
    id: number
    name: string;
    instagram: string;
    shows: ShowInterface[];
}