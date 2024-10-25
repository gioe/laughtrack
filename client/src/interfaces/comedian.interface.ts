import { ShowProviderInterface } from "./showProvider.interface.js";
import { TagInterface } from "./tag.interface.js";

export interface ComedianInterface extends ShowProviderInterface {
  id: number;
  name: string;
  userIsFollower?: boolean;
  favoriteId?: number
  tags?: TagInterface[]
}

export interface ComedianFilterInterface {
  id: number;
  name: string;
}
