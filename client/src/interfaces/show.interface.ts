import { LineupItem } from "./comedian.interface copy.js";

export interface ShowInterface {
  id?: number;
  dateTime: Date;
  ticketLink: string
  clubId: number;
  lineup: LineupItem[];
  popularityScore?: number;
  clubName?: string;

}