export type CreateComedianDTO = {
  name: string;
}

export type MergeComedianDTO = {
  persistantId: number;
  mergedIds: number[];
}

export type UpdateComedianScoreDTO = {
  id: number;
  score: number;
}

export type GetComedianDetailsOutput = {
  id: number;
  name: string;
  instagram_account: string;
  instagram_followers: number;
  tiktok_account: string;
  tiktok_followers: number;
  website: string;
  popularity_score: number;
  is_pseudonym: boolean;
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