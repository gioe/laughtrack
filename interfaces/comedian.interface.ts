import { 
  Favoritable, 
  LineupItemDTO, 
  ShowProvider, 
  GetSocialDataDTO, 
  SocialDiscoverable, 
  GetTagResponseDTO, Taggable
} from "./";

// Client
export interface ComedianInterface extends ShowProvider, SocialDiscoverable, Taggable, Favoritable {
  id: number;
  name: string;
}

export interface ComedianFilterInterface {
  id: number;
  name: string;
}

// DB
export interface GetComediansDTO {
  userId?: number;
}

export interface CreateComedianDTO {
  name: string;
  uuid_id?: string
}

export interface GetComedianResponseDTO {
  id: number;
  name: string;
  social_data: GetSocialDataDTO;
  popularity_score?: number
  dates: GetDateDTO[];
  is_favorite?: boolean;
}

export interface GetDateDTO {
  id: number;
  city: string;
  lineup: LineupItemDTO[]
  club_name: string;
  club_id: number;
  popularity_score: number;
  date_time: Date;
  social_data: GetSocialDataDTO;
  name: string;
  tags: GetTagResponseDTO[]
  price: string;
  ticket_link: string;
}

export interface UpdateComedianRelationshipDTO {
  parent_id: number
  child_id: number;
}

export interface UpdateLineupItemDTO {
  id: number,
  comedian_id: number
}

export interface UpdateComedianHashDTO {
  id: number;
  uuid_id: string
}