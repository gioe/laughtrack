import { LineupItem } from "./lineupItem.interface.js";
import { SocialDataInterface } from "./socialData.interface.js";
import { TagInterface } from "./tag.interface.js";
import { Taggable } from "./taggable.interface.js";

export interface ShowInterface extends Taggable {
  id: number;
  name: string;
  dateTime: Date;
  clubId: number;
  lineup: LineupItem[];
  clubName?: string;
  tags: TagInterface[]
  price: number;
  ticketLink: string;
  socialData?: SocialDataInterface;
}