import { MapCoordinate } from "./mapCoordinate.interface";
import { ShowDetailsInterface } from "./show.interface";

export interface SearchResultResponse {
    city: string;
    shows: ShowDetailsInterface[];
    totalPages: number;
    totalShows: number;
}