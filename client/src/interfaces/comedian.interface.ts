import { ShowInterface } from "./show.interface";

export interface ComedianInterface {
  id?: number;
  name: string;
  socialData?: any;
  dates?: ShowInterface[];
  popularityScore?: number;
}
