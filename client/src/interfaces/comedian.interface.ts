import { ShowDetailsInterface, ShowInterface } from "./show.interface.js";
import { SocialDetailInterface } from "./socialDetail.interface.js";

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
  userIsFollower: boolean;
}

export interface ComedianDetailsInterface {
  id: number;
  name: string;
  socialData: SocialDetailInterface;
  dates: ShowDetailsInterface[]
}

export interface ComedianFilterChipInterface {
  id: number;
  name: string
}