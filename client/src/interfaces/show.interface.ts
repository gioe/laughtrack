import { LineupItem } from "./lineupItem.interface.js";
import { TagInterface } from "./tag.interface.js";

export interface ShowInterface {
  id: number;
  name: string;
  dateTime: Date;
  ticketLink: string
  clubId: number;
  lineup: LineupItem[];
  popularityScore?: number;
  clubName?: string;
  tags?: TagInterface[]
}