import { ShowInterface } from "./show.interface";

export interface SearchResult {
    id: number
    name: string;
    instagram: string;
    shows: ShowInterface[];
}
