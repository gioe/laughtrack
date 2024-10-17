import { GetShowResponseDTO, ShowInterface } from "./show.interface.js";
import { GetSocialDataDTO, SocialDataInterface } from "./socialData.interface.js";

// Client
export interface ClubInterface {
  id: number
  name: string
  baseUrl: string;
  city: string;
  address: string;
  popularityScore: number;
  zipCode: string;
  dates?: ShowInterface[];
  socialData? :SocialDataInterface;
}

export interface ClubScrapingData {
  id: number
  name: string
  baseUrl: string;
  schedulePageUrl: string;
  scrapingConfig: any;
}

// DB
export interface CreateClubDTO {
  id: number;
  name: string;
  city: string;
  address: string
  base_url: string;
  schedule_page_url: string
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
  scraping_config: any;
  zip_code: string;
  popularity_score: number;
  dates?: GetShowResponseDTO[];
  social_data?: GetSocialDataDTO
}

export interface GetCitiesResponseDTO {
  city: string;
}