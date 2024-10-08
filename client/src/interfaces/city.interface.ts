import { ShowProviderInterface } from "./dateContainer.interface.js";
import { ShowInterface } from "./show.interface.js";

export interface CityInterface extends ShowProviderInterface {
  id: number
  name: string
}
