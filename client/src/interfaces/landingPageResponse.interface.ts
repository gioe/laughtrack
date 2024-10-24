import { ComedianInterface } from "./comedian.interface.js";

export interface LandingPageResponseInterface {
  cities: string[];
  trendingComedians: ComedianInterface[];
}

