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

export type GetComedianDetailsOutput = {
  id: number;
  name: string;
  instagram?: string;
}

export type GetComedianShowsOutput = {
  name: string;
  count: number;
  shows: GetShowDetailsOutput[];
}