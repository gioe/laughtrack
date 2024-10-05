import { PopularityScoreDTO } from "./popularityScore.interface.js";
import { GetShowResponseDTO } from "./show.interface.js";

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

export interface GetClubWithShowsResponseDTO {
  id: number;
  name: string;
  popularity_score: number;
  shows: GetShowResponseDTO[]
  base_url: string;
  timezone: string;
  city: string;
  zip_code: string;
  address: string;
}

export interface GetClubPopularityDataDTO {
  id: number;
  scores: PopularityScoreDTO[];
}

export interface GetCitiesResponseDTO {
  city: string;
}