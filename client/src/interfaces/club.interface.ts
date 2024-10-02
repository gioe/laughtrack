import { ShowDetailsInterface } from "./show.interface";

export interface ClubInterface {
    name: string
    url: string;
    address: string;
    longitude: number;
    latitude: number;
}

export interface ClubDetailsInterface {
    id: number;
    name: string;
    city: string;
    longitude: number;
    latitude: number;
    website: string;
    baseUrl: string;
    dates: ShowDetailsInterface[];
}

export interface ClubFilterChipInterface {
    id: number;
    name: string;
}