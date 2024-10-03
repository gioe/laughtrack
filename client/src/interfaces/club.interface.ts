import { ShowInterface } from "./show.interface";

export interface ClubInterface {
  id?: number
  name: string
  baseUrl: string;
  schedulePageUrl: string;
  timezone: string;
  scrapingConfig: any;
  city: string;
  address: string;
  latitude: number;
  longitude: number;
  popularityScore: number;
  zipCode: string;
  shows?: ShowInterface[];
}