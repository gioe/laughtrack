import { GetShowDetailsOutput } from "./show.dto.js";

export type CreateComedianDTO = {
  name: string;
}

export type MergeComedianDTO = {
  persistantId: number;
  mergedIds: number[];
}

export type GetComedianDetailsOutput = {
  id: number;
  name: string;
  instagram_account: string;
  tiktok_account: string;
  website: string;
  popularity_score: number;
}

export type CreateComedianOutput = {
  id: number;
}

export type GetSearchResultsOutput = {
  comedian_id: number;
  comedian_name: string;
  instagram: string;
  date_time?: Date;
  ticket_link: string;
  address: string;
  base_url: string;
  club_name: string
  latitude: number,
  longitude: number;
  show_id: number;
}

export type ComedianPopularityDTO = {
  instagramFollowers: number | null;
  tiktokFollowers: number | null;
  isPseudoynm: number | null;
}