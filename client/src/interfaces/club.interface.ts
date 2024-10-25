import { ShowProviderInterface } from "./showProvider.interface.js";
import { TagInterface } from "./tag.interface.js";

export interface ClubInterface extends ShowProviderInterface {
  id: number
  name: string
  baseUrl: string;
  city: string;
  address: string;
  popularityScore: number;
  zipCode: string;
  tags?: TagInterface[]
}

export interface ClubScrapingData {
  id: number
  name: string
  baseUrl: string;
  schedulePageUrl: string;
}