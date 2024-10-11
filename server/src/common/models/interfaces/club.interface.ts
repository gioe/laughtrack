import { GetShowResponseDTO, ShowInterface } from "./show.interface.js";

// Client
export interface ClubInterface {
  id: number
  name: string
  baseUrl: string;
  timezone: string;
  city: string;
  address: string;
  popularityScore: number;
  zipCode: string;
  dates?: ShowInterface[];
}

export interface ClubScrapingData {
  id: number
  name: string
  baseUrl: string;
  schedulePageUrl: string;
  scrapingConfig: any;
}

//DB


export interface CreateClubDTO {
  id: number;
  name: string;
  city: string;
  address: string
  base_url: string;
  schedule_page_url: string
  timezone: string;
  scraping_config: any;
  zip_code: string;
  popularity_score: number;
}

export interface GetClubDTO {
  id: number;
  name: string;
  city: string;
  address: string
  base_url: string;
  schedule_page_url: string
  timezone: string;
  scraping_config: any;
  zip_code: string;
  popularity_score: number;
  dates?: GetShowResponseDTO[];
}

export interface GetCitiesResponseDTO {
  city: string;
}

export interface GetClubsDTO {
  sort?: string;
  query?: string;
}