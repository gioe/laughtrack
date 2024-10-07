import { ShowProviderInterface } from "./dateContainer.interface.js";
import { ShowInterface } from "./show.interface.js";

export interface ClubInterface extends ShowProviderInterface {
  id: number
  name: string
  baseUrl: string;
  timezone: string;
  city: string;
  address: string;
  popularityScore: number;
  zipCode: string;
}

export interface ClubScrapingData {
  id: number
  name: string
  baseUrl: string;
  schedulePageUrl: string;
  scrapingConfig: any;
}