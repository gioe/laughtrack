import { ShowInterface } from "./show.interface.js";

export interface ClubInterface {
  id: number
  name: string
  baseUrl: string;
  timezone: string;
  city: string;
  address: string;
  popularityScore: number;
  zipCode: string;
  shows?: ShowInterface[];
}

export interface ClubScrapingData {
  id: number
  name: string
  baseUrl: string;
  schedulePageUrl: string;
  scrapingConfig: any;
}