import { Comedian } from "../classes/Comedian";
import { 
  ComedianInterface, LineupItemDTO, GetSocialDataDTO, 
  SocialDataInterface, GetTagResponseDTO, Taggable 
} from ".";


// Client
export interface ShowInterface extends Taggable {
  id: number;
  name: string;
  dateTime: Date;
  socialData: SocialDataInterface;
  clubId: number;
  lineup: ComedianInterface[];
  popularityScore?: number;
  clubName?: string;
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