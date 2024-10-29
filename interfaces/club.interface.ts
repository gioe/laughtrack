import { 
  Taggable, 
  GetSocialDataDTO, 
  SocialDiscoverable, 
  ShowProvider, 
  GetShowResponseDTO, 
  Favoritable
} from "./";

// Client

export interface ClubInterface extends ShowProvider, SocialDiscoverable, Taggable, Favoritable {
  id: number
  name: string
  baseUrl: string;
  city: string;
  address: string;
  zipCode: string;
}

export interface ClubScrapingData {
  id: number
  name: string
  baseUrl: string;
  schedulePageUrl: string;
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
  social_data: GetSocialDataDTO
}


