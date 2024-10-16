import { Comedian } from "../classes/Comedian.js";
import { LineupItem, LineupItemDTO } from "./lineupItem.interface.js";

// Client
export interface TagInterface {
  id: number;
  name: string;
}

// DB
export interface GetTagDTO {
  type: string;
}

export interface GetTagResponseDTO {
  id: number;
  tag_name: string;
  type: string;
  user_facing: boolean;
}

