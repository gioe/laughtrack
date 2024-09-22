import { ShowInterface } from "./show.interface.js";

export interface ComedianInterface {
  id: number
  name: string
  instagram: string
  shows: ShowInterface[];
}