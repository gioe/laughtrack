import { ShowInterface } from "./show.interface.js";
import { SocialDataInterface } from "./socialData.interface.js";

export interface ShowProviderInterface {
  id: number;
  dates: ShowInterface[];
  name: string;
  socialData?: SocialDataInterface;
}

