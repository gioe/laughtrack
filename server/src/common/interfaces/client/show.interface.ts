import { LineupItem } from "./lineupItem.interface.js";
import { ComedianInterface } from "./comedian.interface.js";

export interface ShowInterface {
  id?: number;
  dateTime: Date;
  ticketLink: string
  clubId: number;
  lineup: LineupItem[];
  popularityScore?: number;
  clubName?: string;
  
}