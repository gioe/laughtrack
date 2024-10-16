import { SocialDataInterface } from "./socialData.interface";

export interface LineupItem {
  id: number;
  name: string;
  popularityScore: number;
  favoriteId?: number
  socialData?: SocialDataInterface;
}
