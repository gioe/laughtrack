import { ShowInterface } from "./show.interface.js";

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
    imageName: string;
    popularityScore: number;
    shows?: ShowInterface[]
}

export interface ClubPopularityScore {
    id: number;
    popularity_score: number
  }

  export interface ClubDetailsInterface {
    name: string;
  }