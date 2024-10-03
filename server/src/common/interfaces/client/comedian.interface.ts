import { ShowInterface } from "./show.interface.js";

export interface ComedianInterface {
  id?: number;
  name: string;
  socialData?: any;
  dates?: ShowInterface[];
  popularityScore?: number;
}
