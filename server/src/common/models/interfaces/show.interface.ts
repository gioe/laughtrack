import { Comedian } from "../classes/Comedian.js";
import { LineupItem, LineupItemDTO } from "./lineupItem.interface.js";

// Client
export interface ShowInterface {
  id?: number;
  name?: string;
  dateTime: Date;
  ticketLink: string;
  clubId: number;
  lineup: LineupItem[];
  popularityScore?: number;
  clubName?: string;
}

export interface ShowInput {
  lineup: Comedian[];
  dateTime: Date;
  ticketLink: string;
  name: string;
}


// DB
export interface CreateShowDTO {
  club_id: number;
  date_time: Date;
  ticket_link: string;
  name: string;
}

export interface GetShowResponseDTO {
  id: number;
  club_id: number;
  club_name: string;
  date_time: Date;
  ticket_link: string;
  popularity_score: number;
  lineup: LineupItemDTO[];
}