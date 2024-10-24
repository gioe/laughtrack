import { LineupItemDTO } from "./lineupItem.interface.js";
import { ShowInterface } from "./show.interface.js";
import { GetSocialDataDTO, SocialDataInterface } from "./socialData.interface.js";
import { GetTagDTO, GetTagResponseDTO } from "./tag.interface.js";

// Client
export interface ComedianInterface {
  id?: number;
  name: string;
  socialData?: SocialDataInterface;
  dates?: ShowInterface[];
  favoriteId?: number
  popularityScore?: number;
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
  favorite_id?: number;
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