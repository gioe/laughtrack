import { ShowProviderInterface } from "./dateContainer.interface.js";
import { ShowInterface } from "./show.interface.js";

export interface ComedianInterface extends ShowProviderInterface {
  id?: number;
  name: string;
  userIsFollower?: boolean;
  favoriteId?: number
}
