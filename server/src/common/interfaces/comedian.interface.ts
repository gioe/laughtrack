import { ShowDetailsInterface } from "./show.interface.js";
import { SocialDatailInterface } from "./socialData.interface.js";

export interface ComedianInterface {
  id: number
  name: string
  instagramAccount?: string
  tikTokAccount?: string  
  website?: string,
  poplarityScore: number;
  instagramFollowers: number;
  tiktokFollowers: number;
  isPseudonym: boolean;
}

export interface ComedianPopularityScore {
  id: number;
  popularity_score: number
}

export interface ComedianDetailsInterface {
  id: number;
  name: string;
  socialData: SocialDatailInterface;
  shows: ShowDetailsInterface[]
}