import { TagInterface } from "./tag.interface";

export interface Taggable {
  id: number;
  tags: TagInterface[];
}