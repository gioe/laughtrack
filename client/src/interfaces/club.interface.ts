import { ShowProviderInterface } from "./showProvider.interface.js";

export interface ClubInterface extends ShowProviderInterface {
  id: number
  name: string
  baseUrl: string;
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
}