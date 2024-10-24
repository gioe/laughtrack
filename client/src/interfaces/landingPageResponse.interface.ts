import { ComedianInterface } from "./comedian.interface.js";
import { ShowInterface } from "./show.interface.js";
import { SocialDataInterface } from "./socialData.interface.js";

export interface LandingPageResponseInterface {
  cities: string[];
  trendingComedians: ComedianInterface[];
}

