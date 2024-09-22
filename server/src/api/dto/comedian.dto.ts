import { GetShowDetailsOutput } from "./show.dto.js";

export type CreateComedianDTO = {
  name: string;
  instagram?: string;
  slug?: string;
}

export type MergeComedianDTO = {
  persistantId: number;
  mergedIds: number[];
}

export type GetComedianDetailsOutput = {
  id: number;
  name: string;
  instagram: string;
}

export type CreateComedianOutput = {
  id: number;
}

export type UpdateComedianDTO = {
  name: string;
  slug?: string;
}

export type ComedianExistenceDTO = {
  name: string;
}

export type GetShowComedianDetailsOutput = {
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

export type GetComedianShowsOutput = {
  name: string;
  count: number;
  shows: GetShowDetailsOutput[];
}

export type TrendingComedian = {
  id: number;
  name: string;
  instagram: string;
  count: number;
}