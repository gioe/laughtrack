import { ShowInterface } from "./show.interface.js";
import { SocialDataInterface } from "./socialData.interface.js";

export interface ComedianInterface {
  id?: number;
  name: string;
  socialData?: SocialDataInterface;
  dates?: ShowInterface[];
  favoriteId?: number
}
