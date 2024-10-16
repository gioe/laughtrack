import { ShowInterface } from "./show.interface.js";
import { SocialDataInterface } from "./socialData.interface.js";

export interface BannerProviderInterface {
  id: number;
  name: string;
  socialData?: SocialDataInterface;
}

