import { ShowDetailsInterface, ShowInterface } from "./show.interface.js";

export interface ClubInterface {
    id: number
    name: string
    baseUrl: string;
    schedulePageUrl: string;
    timezone: string;
    scrapingConfig: any;
    city: string;
    address: string;
    latitude: number;
    longitude: number;
    popularityScore: number;
    shows?: ShowInterface[];
    zipCode: string;
}

export interface ClubPopularityScore {
    id: number;
    popularity_score: number
  }

  export interface ClubDetailsInterface {
    id: number;
    name: string;
    city: string;
    longitude: number;
    latitude: number;
    baseUrl: string;
    shows: ShowDetailsInterface[];
    zipCode: string;
  }