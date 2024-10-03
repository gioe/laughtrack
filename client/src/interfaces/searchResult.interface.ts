import { ShowInterface } from "./show.interface";

export interface HomeSearchResultInterface {
    city: string;
    shows: ShowInterface[];
    totalPages?: number;
    totalShows?: number;
}