import { ShowProviderInterface } from "./showProvider.interface.js";
import { ShowInterface } from "./show.interface.js";

export interface ComedianInterface extends ShowProviderInterface {
  id: number;
  name: string;
  userIsFollower?: boolean;
  favoriteId?: number
}

export interface ComedianFilterInterface {
  id: number;
  name: string;
}
