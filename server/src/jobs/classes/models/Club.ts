import { ClubInterface } from "../../../common/interfaces/club.interface.js";
import { ShowInterface } from "../../../common/interfaces/show.interface.js";

export class Club implements ClubInterface {
  
  id: number = 0;
  zipCode: string = "";
  name: string = "";
  baseUrl: string = "";
  schedulePageUrl: string = "";
  timezone: string = "";
  scrapingConfig: any;
  city: string = "";
  address: string = "";
  latitude: number = 0;
  longitude: number = 0;
  imageName: string = ""
  popularityScore = 0;
  shows?: ShowInterface[] | undefined;

  constructor() {
  }

}