import { ShowInterface } from "./show.interface.js";

export interface ComedianInterface {
  id: number
  name: string
  instagram: string
  shows: ShowInterface[];
  instagramAccount: string;
  instagramFollowers: number;
  tiktokAccount: string;
  tiktokFollowers: number;
  website: string;
  isPseudonym: boolean;
  popularityScore: any;
  nonComedian: boolean;
}