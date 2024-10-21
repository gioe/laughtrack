import { Comedian } from "../classes/Comedian.js";
import { LineupItem, LineupItemDTO } from "./lineupItem.interface.js";
import { GetSocialDataDTO, SocialDataInterface } from "./socialData.interface.js";
import { GetTagDTO, GetTagResponseDTO, TagInterface } from "./tag.interface.js";

// Client
export interface ShowInterface {
  id?: number;
  name?: string;
  dateTime: Date;
  socialData: SocialDataInterface;
  clubId: number;
  lineup: LineupItem[];
  popularityScore?: number;
  clubName?: string;
  tags: TagInterface[]
  price: number;
  ticketLink: string;
}

export interface ShowInput {
  lineup: Comedian[];
  dateTime: Date;
  ticketLink: string;
  name: string;
  price: string;
  clubId: number;
}

// DB
export interface CreateShowDTO {
  club_id: number;
  date_time: Date;
  ticket_link: string;
  name: string;
  price: string
}

export interface GetShowResponseDTO {
  id: number;
  date_time: Date;
  social_data: GetSocialDataDTO;
  name: string;
  club_id: number;
  club_name: string;
  base_url: string;
  popularity_score: number;
  lineup: LineupItemDTO[];
  tags: GetTagResponseDTO[]
  price: string;
  ticket_link: string;
}